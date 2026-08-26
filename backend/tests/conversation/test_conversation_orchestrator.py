"""Focused multi-turn orchestration tests without graph tools or provider I/O."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from backend.app.conversation.exceptions import (
    IntentClassificationError,
    MissingLocationError,
)
from backend.app.conversation.intent import IntentClassification, IntentLabel
from backend.app.conversation.models import (
    ConversationMode,
    ConversationResponseType,
    ConversationTurn,
)
from backend.app.conversation.orchestrator import ConversationOrchestrator
from backend.app.conversation.session_store import ConversationSessionStore
from backend.app.decision.exceptions import DecisionGenerationError
from backend.app.decision.models import (
    Decision,
    DecisionConfidence,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)
from backend.app.decision.prompt_builder import PromptBuilder
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.state import (
    Coordinate,
    EvidenceBundle,
    GraphState,
    KnowledgeEvidence,
    UserRequest,
)
from backend.app.observability.context import ExecutionContext
from backend.app.rag.models import Citation, GroundedAnswer


def _decision(summary: str) -> Decision:
    """Create a minimal valid decision returned by the injected test agent."""
    return Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.LOW,
            rationale="Policy guidance.",
        ),
        recommendation=Recommendation(summary=summary),
        confidence=DecisionConfidence.LOW,
    )


class _GraphRuntimeSpy:
    """Return configured bundles while recording every requested graph execution."""

    def __init__(
        self,
        bundles: tuple[EvidenceBundle, ...],
        decisions: tuple[Decision | None, ...],
    ) -> None:
        self._bundles = bundles
        self._decisions = decisions
        self.inputs: list[GraphState] = []

    async def execute(self, state: GraphState) -> GraphState:
        """Return the next evidence bundle as an immutable graph result."""
        self.inputs.append(state)
        index = len(self.inputs) - 1
        return state.model_copy(
            update={
                "evidence_bundle": self._bundles[index],
                "decision": self._decisions[index],
            }
        )


class _DecisionAgentSpy:
    """Return deterministic decisions while retaining active evidence and history."""

    def __init__(self) -> None:
        self.calls: list[tuple[EvidenceBundle, tuple[ConversationTurn, ...], str]] = []

    async def decide(
        self,
        evidence: EvidenceBundle,
        *,
        execution_context: ExecutionContext | None = None,
        history: Sequence[ConversationTurn] = (),
        current_request_text: str = "",
    ) -> Decision:
        """Capture one agent call without invoking a provider."""
        del execution_context
        self.calls.append((evidence, tuple(history), current_request_text))
        return _decision(f"decision-{len(self.calls)}")


class _KnowledgeToolSpy:
    """Return a scripted grounded answer while recording every question asked."""

    def __init__(self, answer: GroundedAnswer | None = None) -> None:
        self._answer = answer or GroundedAnswer("No relevant guidance found.", ())
        self.questions: list[str] = []

    def answer(self, question: str, top_k: int = 5) -> GroundedAnswer:
        """Capture one question without invoking a real retriever."""
        del top_k
        self.questions.append(question)
        return self._answer


class _IntentClassifierSpy:
    """Return a scripted classification (or raise) while recording every call.

    Defaults to ``GENUINE_QUESTION``, which the orchestrator treats
    identically to "classification unavailable" -- i.e. every existing
    scenario that predates intent classification keeps behaving exactly as
    it did before this collaborator existed, with zero script changes
    required at those call sites.
    """

    def __init__(
        self,
        classification: IntentClassification | None = None,
        *,
        classifications: Sequence[IntentClassification] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._classification = classification or IntentClassification(
            label=IntentLabel.GENUINE_QUESTION
        )
        self._classifications = (
            list(classifications) if classifications is not None else None
        )
        self._error = error
        self.calls: list[
            tuple[str, ConversationMode, tuple[ConversationTurn, ...], bool]
        ] = []

    async def classify(
        self,
        request_text: str,
        *,
        mode: ConversationMode,
        history: Sequence[ConversationTurn] = (),
        has_location: bool = False,
    ) -> IntentClassification:
        """Record one classification request and return or raise as scripted.

        ``classifications``, when supplied, is consumed in call order (one
        per turn) -- mirrors ``_GraphRuntimeSpy``'s per-call bundle sequencing
        -- for scenarios where different turns must classify differently.
        """
        self.calls.append((request_text, mode, tuple(history), has_location))
        if self._error is not None:
            raise self._error
        if self._classifications:
            return self._classifications.pop(0)
        return self._classification


def _state_factory() -> GraphStateFactory:
    """Create a deterministic factory with enough UUIDs for multi-turn tests."""
    identifiers = iter(UUID(int=index) for index in range(1, 32))
    timestamp = datetime(2026, 7, 28, tzinfo=UTC)
    return GraphStateFactory(
        uuid_factory=lambda: next(identifiers),
        clock=lambda: timestamp,
    )


def _orchestrator(
    bundles: tuple[EvidenceBundle, ...],
    decisions: tuple[Decision | None, ...] | None = None,
    knowledge_tool: _KnowledgeToolSpy | None = None,
    session_store: ConversationSessionStore | None = None,
    intent_classifier: _IntentClassifierSpy | None = None,
):
    """Build isolated collaborators for one scripted conversation scenario."""
    runtime = _GraphRuntimeSpy(
        bundles,
        decisions
        or tuple(
            _decision(f"graph-decision-{index}")
            for index in range(1, len(bundles) + 1)
        ),
    )
    agent = _DecisionAgentSpy()
    knowledge = knowledge_tool or _KnowledgeToolSpy()
    orchestrator = ConversationOrchestrator(
        graph_runtime=runtime,
        decision_agent=agent,
        prompt_builder=PromptBuilder(),
        session_store=session_store or ConversationSessionStore(),
        state_factory=_state_factory(),
        knowledge_tool=knowledge,
        intent_classifier=intent_classifier or _IntentClassifierSpy(),
        clock=lambda: datetime(2026, 7, 28, tzinfo=UTC),
    )
    return orchestrator, runtime, agent, knowledge


def _bundle(citation: str) -> EvidenceBundle:
    """Create distinct but grounded evidence identities for reuse assertions."""
    return EvidenceBundle(knowledge=KnowledgeEvidence(citations=(citation,)))


def test_prompt_history_contains_only_prior_request_and_summary() -> None:
    """History must provide continuity without embedding prior evidence payloads."""
    bundle = _bundle("PDMA Plan")
    turn = ConversationTurn(
        request_text="Flood outlook for Mingora?",
        village_name="Mingora",
        evidence_bundle=bundle,
        decision=_decision("Prepare local response."),
        summary="Prepare local response.",
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )

    _, user_prompt = PromptBuilder().build(
        bundle, history=(turn,), current_request_text="What about shelters?"
    )

    assert "Conversation history:" in user_prompt
    assert "Flood outlook for Mingora?" in user_prompt
    assert "Prepare local response." in user_prompt
    assert "Current request:" in user_prompt
    assert "What about shelters?" in user_prompt
    assert (
        user_prompt.index("Conversation history:")
        < user_prompt.index("Current request:")
        < user_prompt.index("EvidenceBundle:")
    )
    assert "Conversation history:" not in PromptBuilder().build(bundle)[1]
    assert "Current request:" not in PromptBuilder().build(bundle)[1]


def test_same_village_follow_up_reuses_evidence_without_graph_execution() -> None:
    """A follow-up with unchanged location context must not invoke graph tools."""
    first_bundle = _bundle("PDMA Plan")
    orchestrator, runtime, agent, _knowledge = _orchestrator((first_bundle,))
    request = UserRequest(request_text="Flood outlook?", village_name="Mingora")

    session_id, _ = asyncio.run(orchestrator.handle_turn(None, request))
    _, second = asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="What about shelters?", village_name="Mingora"),
        )
    )

    assert len(runtime.inputs) == 1
    assert [call[0] for call in agent.calls] == [first_bundle]
    assert second.decision is not None
    assert second.decision.recommendation.summary == "decision-1"
    assert agent.calls[0][2] == "What about shelters?", (
        "The reuse-path decide() call must receive the CURRENT turn's own "
        "request text, not the prior turn's, so the model can actually see "
        "what this turn specifically asks about."
    )


def test_changed_village_runs_graph_again() -> None:
    """Changing the village must refresh the active evidence bundle."""
    first_bundle, second_bundle = _bundle("Mingora Plan"), _bundle("Saidu Plan")
    orchestrator, runtime, agent, _knowledge = _orchestrator((first_bundle, second_bundle))

    session_id, _ = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="Flood outlook?", village_name="Mingora"),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="Flood outlook?", village_name="Saidu Sharif"),
        )
    )

    assert len(runtime.inputs) == 2
    assert not agent.calls


def test_consecutive_same_context_follow_ups_grow_history_without_refetching() -> None:
    """Repeated local follow-ups reuse evidence and preserve ordered history."""
    bundle = _bundle("PDMA Plan")
    orchestrator, runtime, agent, _knowledge = _orchestrator((bundle,))
    request = UserRequest(request_text="Flood outlook?", village_name="Mingora")

    session_id, _ = asyncio.run(orchestrator.handle_turn(None, request))
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            request.model_copy(update={"request_text": "What about shelters?"}),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            request.model_copy(update={"request_text": "And evacuation?"}),
        )
    )

    assert len(runtime.inputs) == 1
    assert [len(history) for _, history, _ in agent.calls] == [1, 2]


def test_reuse_tracks_the_most_recent_changed_context() -> None:
    """Follow-ups after a context change reuse the latest, not original, evidence."""
    first_bundle, second_bundle = _bundle("Mingora Plan"), _bundle("Saidu Plan")
    orchestrator, runtime, agent, _knowledge = _orchestrator((first_bundle, second_bundle))
    session_id, _ = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="Flood outlook?", village_name="Mingora"),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="Flood outlook?", village_name="Saidu Sharif"),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="What about shelters?", village_name="Saidu Sharif"),
        )
    )

    assert len(runtime.inputs) == 2
    assert [call[0] for call in agent.calls] == [second_bundle]


def test_agent_receives_active_evidence_and_ordered_prior_summaries() -> None:
    """Every turn must retain only prior decision summaries as conversation context."""
    first_bundle, second_bundle = _bundle("Mingora Plan"), _bundle("Saidu Plan")
    orchestrator, _, agent, _knowledge = _orchestrator((first_bundle, second_bundle))
    session_id, _ = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="First", village_name="Mingora"),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="Second", village_name="Saidu Sharif"),
        )
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="Third", village_name="Saidu Sharif"),
        )
    )

    third_evidence, third_history, _ = agent.calls[0]
    assert third_evidence is second_bundle
    assert [turn.recommendation_summary for turn in third_history] == [
        "graph-decision-1",
        "graph-decision-2",
    ]


def test_graph_fallback_without_canonical_decision_does_not_retry_provider() -> None:
    """A graph fallback cannot be represented as a real typed conversation turn."""
    bundle = _bundle("PDMA Plan")
    orchestrator, runtime, agent, _knowledge = _orchestrator((bundle,), decisions=(None,))

    with pytest.raises(DecisionGenerationError):
        asyncio.run(
            orchestrator.handle_turn(
                None,
                UserRequest(request_text="Flood outlook?", village_name="Mingora"),
            )
        )

    assert len(runtime.inputs) == 1
    assert not agent.calls


def test_flood_agent_mode_requires_location() -> None:
    """A flood-risk question with no coordinates or village name must be rejected before the graph runs."""
    orchestrator, runtime, agent, _knowledge = _orchestrator(())

    with pytest.raises(MissingLocationError):
        asyncio.run(
            orchestrator.handle_turn(
                None,
                UserRequest(request_text="What is the current flood condition here?"),
            )
        )

    assert not runtime.inputs
    assert not agent.calls


def test_flood_agent_mode_rejects_whitespace_only_village_name() -> None:
    """A blank/whitespace-only village name (e.g. an unfilled 'Other' field) is not a location."""
    orchestrator, runtime, _agent, _knowledge = _orchestrator(())

    with pytest.raises(MissingLocationError):
        asyncio.run(
            orchestrator.handle_turn(
                None,
                UserRequest(request_text="Flood outlook?", village_name="   "),
            )
        )

    assert not runtime.inputs


def test_flood_agent_mode_accepts_coordinates_without_village_name() -> None:
    """Coordinates alone satisfy the location requirement."""
    bundle = _bundle("PDMA Plan")
    orchestrator, runtime, _agent, _knowledge = _orchestrator((bundle,))

    asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(
                request_text="Flood outlook?",
                coordinates=Coordinate(latitude=34.77, longitude=72.36),
            ),
        )
    )

    assert len(runtime.inputs) == 1


def test_small_talk_short_circuits_without_graph_or_decision_agent() -> None:
    """A casual greeting must never invoke the graph, decision agent, or RAG."""
    orchestrator, runtime, agent, knowledge = _orchestrator(())

    _, outcome = asyncio.run(
        orchestrator.handle_turn(None, UserRequest(request_text="hi"))
    )

    assert not runtime.inputs
    assert not agent.calls
    assert not knowledge.questions
    assert outcome.response_type is ConversationResponseType.SMALL_TALK
    assert outcome.decision is None
    assert outcome.citations == ()
    assert outcome.summary


def test_small_talk_turn_is_recorded_for_session_continuity() -> None:
    """A small-talk turn must still be appended so history stays coherent."""
    store = ConversationSessionStore()
    orchestrator, _, _, _ = _orchestrator((), session_store=store)

    session_id, outcome = asyncio.run(
        orchestrator.handle_turn(None, UserRequest(request_text="hi"))
    )

    session = asyncio.run(store.get_session(session_id))
    assert session is not None
    assert len(session.turns) == 1
    recorded = session.turns[0]
    assert recorded.decision is None
    assert recorded.summary == outcome.summary
    assert recorded.evidence_bundle == EvidenceBundle()


def test_small_talk_reply_is_mode_aware() -> None:
    """The canned reply must differ between flood-agent and policy-advisor modes."""
    flood_orchestrator, _, _, _ = _orchestrator(())
    policy_orchestrator, _, _, _ = _orchestrator(())

    _, flood_outcome = asyncio.run(
        flood_orchestrator.handle_turn(
            None, UserRequest(request_text="hi"), mode=ConversationMode.FLOOD_AGENT
        )
    )
    _, policy_outcome = asyncio.run(
        policy_orchestrator.handle_turn(
            None, UserRequest(request_text="hi"), mode=ConversationMode.POLICY_ADVISOR
        )
    )

    assert flood_outcome.summary != policy_outcome.summary


def test_policy_advisor_mode_calls_knowledge_tool_only() -> None:
    """Policy-advisor mode must answer from RAG alone, never the flood graph."""
    scripted_answer = GroundedAnswer(
        "District authorities must pre-position relief stock.",
        (Citation("NDMP", 12, "Relief Stock"),),
    )
    store = ConversationSessionStore()
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), knowledge_tool=_KnowledgeToolSpy(scripted_answer), session_store=store
    )

    session_id, outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What does government policy require?"),
            mode=ConversationMode.POLICY_ADVISOR,
        )
    )

    assert not runtime.inputs
    assert not agent.calls
    assert knowledge.questions == ["What does government policy require?"]
    assert outcome.response_type is ConversationResponseType.POLICY_ANSWER
    assert outcome.decision is None
    assert outcome.summary == scripted_answer.text
    assert outcome.citations == ("NDMP:p12:Relief Stock",)

    session = asyncio.run(store.get_session(session_id))
    assert session is not None
    recorded = session.turns[0]
    assert recorded.decision is None
    assert recorded.summary == scripted_answer.text
    assert recorded.evidence_bundle.knowledge.citations == ("NDMP:p12:Relief Stock",)


def test_policy_advisor_mode_ignores_small_talk_free_text() -> None:
    """A real policy question in policy-advisor mode must not be misread as small talk."""
    orchestrator, runtime, agent, knowledge = _orchestrator(())

    asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What is the government's evacuation policy?"),
            mode=ConversationMode.POLICY_ADVISOR,
        )
    )

    assert not runtime.inputs
    assert not agent.calls
    assert knowledge.questions == ["What is the government's evacuation policy?"]


def test_exact_small_talk_phrase_never_invokes_intent_classifier() -> None:
    """The zero-cost phrase-list path must not pay for an LLM classification call."""
    classifier = _IntentClassifierSpy()
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    asyncio.run(orchestrator.handle_turn(None, UserRequest(request_text="hi")))

    assert not classifier.calls
    assert not runtime.inputs
    assert not agent.calls
    assert not knowledge.questions


def test_genuine_follow_up_after_capability_question_runs_fresh_evidence() -> None:
    """A genuine question right after a capability question must not reuse its empty evidence.

    Regression test for a real bug found in live manual testing: a
    capability-question (or clarification) turn records an empty
    EvidenceBundle() while still carrying the request's real, unchanged
    location. requires_new_evidence only compares location fields, so a
    same-location follow-up was wrongly treated as reusable, starving a
    genuine question of all evidence (missing_evidence listing every
    category, citations empty) even though a real village was selected
    throughout the conversation.
    """
    bundle = _bundle("PDMA Plan")
    classifier = _IntentClassifierSpy(
        classifications=[
            IntentClassification(
                label=IntentLabel.CAPABILITY_QUESTION,
                response_text="I assess flood risk for villages in Swat district.",
            ),
            IntentClassification(label=IntentLabel.GENUINE_QUESTION),
        ]
    )
    orchestrator, runtime, agent, _knowledge = _orchestrator(
        (bundle,), intent_classifier=classifier
    )

    session_id, first_outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="How can you help me?", village_name="Mingora"),
        )
    )
    assert first_outcome.response_type is ConversationResponseType.CAPABILITY_QUESTION

    _, second_outcome = asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(
                request_text="What is the current flood condition?",
                village_name="Mingora",
            ),
        )
    )

    assert len(runtime.inputs) == 1, (
        "The genuine follow-up must run the evidence graph fresh, not reuse "
        "the capability-question turn's empty evidence bundle."
    )
    assert second_outcome.response_type is ConversationResponseType.FLOOD_DECISION
    assert second_outcome.decision is not None
    assert not agent.calls, "A fresh graph run supplies its own decision directly."


def test_capability_question_short_circuits_without_location_or_pipeline() -> None:
    """A capability question must never require location or run the flood pipeline."""
    classifier = _IntentClassifierSpy(
        IntentClassification(
            label=IntentLabel.CAPABILITY_QUESTION,
            response_text="I assess flood risk for villages in Swat district.",
        )
    )
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    _, outcome = asyncio.run(
        orchestrator.handle_turn(
            None, UserRequest(request_text="How can you help me?")
        )
    )

    assert classifier.calls == [
        ("How can you help me?", ConversationMode.FLOOD_AGENT, (), False)
    ]
    assert not runtime.inputs
    assert not agent.calls
    assert not knowledge.questions
    assert outcome.response_type is ConversationResponseType.CAPABILITY_QUESTION
    assert outcome.decision is None
    assert outcome.summary == "I assess flood risk for villages in Swat district."


def test_classifier_receives_has_location_true_for_a_resolved_follow_up() -> None:
    """A follow-up that already carries a village name must tell the classifier so.

    Regression guard: the classifier previously received only raw request
    text, with no visibility into the request's own resolved location, so
    it could not reliably distinguish "no location established" from
    "location established, something else is vague" -- causing real
    follow-ups like "What about shelters?" in an established conversation
    to be wrongly asked "which village?" again.
    """
    classifier = _IntentClassifierSpy()
    orchestrator, runtime, agent, _knowledge = _orchestrator(
        (_bundle("PDMA Plan"),), intent_classifier=classifier
    )

    asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What about shelters?", village_name="Mingora"),
        )
    )

    assert classifier.calls[0][3] is True


def test_classifier_receives_has_location_false_without_coordinates_or_village() -> None:
    """A capability/ambiguous question asked before selecting a location must say so."""
    classifier = _IntentClassifierSpy(
        IntentClassification(label=IntentLabel.CAPABILITY_QUESTION, response_text="x")
    )
    orchestrator, _runtime, _agent, _knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    asyncio.run(
        orchestrator.handle_turn(None, UserRequest(request_text="How can you help me?"))
    )

    assert classifier.calls[0][3] is False


def test_capability_question_in_policy_advisor_mode_never_calls_knowledge_tool() -> None:
    """A capability question in Policy Advisor mode must not trigger real RAG retrieval."""
    classifier = _IntentClassifierSpy(
        IntentClassification(
            label=IntentLabel.CAPABILITY_QUESTION,
            response_text="I answer from real PDMA/NDMP documents.",
        )
    )
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    _, outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What can I ask you?"),
            mode=ConversationMode.POLICY_ADVISOR,
        )
    )

    assert not knowledge.questions
    assert outcome.response_type is ConversationResponseType.CAPABILITY_QUESTION
    assert outcome.summary == "I answer from real PDMA/NDMP documents."


def test_needs_clarification_short_circuits_and_is_recorded_for_history() -> None:
    """An ambiguous question must produce a clarifying question, not a guess."""
    classifier = _IntentClassifierSpy(
        IntentClassification(
            label=IntentLabel.NEEDS_CLARIFICATION,
            response_text="Which village or coordinates would you like me to assess?",
        )
    )
    store = ConversationSessionStore()
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), intent_classifier=classifier, session_store=store
    )

    session_id, outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(
                request_text="Is it safe?",
                coordinates=Coordinate(latitude=34.77, longitude=72.36),
            ),
        )
    )

    assert not runtime.inputs
    assert not agent.calls
    assert not knowledge.questions
    assert outcome.response_type is ConversationResponseType.NEEDS_CLARIFICATION
    assert outcome.decision is None
    assert outcome.summary == "Which village or coordinates would you like me to assess?"

    session = asyncio.run(store.get_session(session_id))
    assert session is not None
    recorded = session.turns[0]
    assert recorded.decision is None
    assert recorded.summary == outcome.summary
    assert recorded.evidence_bundle == EvidenceBundle()


def test_clarification_turn_is_visible_to_next_turns_classification_history() -> None:
    """A follow-up must let the classifier see the clarifying question just asked."""
    classifier = _IntentClassifierSpy(
        IntentClassification(
            label=IntentLabel.NEEDS_CLARIFICATION,
            response_text="Which village would you like me to assess?",
        )
    )
    orchestrator, _runtime, _agent, _knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    session_id, _ = asyncio.run(
        orchestrator.handle_turn(None, UserRequest(request_text="Is it safe?"))
    )
    asyncio.run(
        orchestrator.handle_turn(
            session_id,
            UserRequest(request_text="Mingora", village_name="Mingora"),
        )
    )

    second_call_history = classifier.calls[1][2]
    assert len(second_call_history) == 1
    assert second_call_history[0].request_text == "Is it safe?"
    assert (
        second_call_history[0].recommendation_summary
        == "Which village would you like me to assess?"
    )


def test_classifier_failure_falls_back_to_full_flood_pipeline() -> None:
    """A classifier outage must never block or misroute a flood-agent turn."""
    bundle = _bundle("PDMA Plan")
    classifier = _IntentClassifierSpy(error=IntentClassificationError("boom"))
    orchestrator, runtime, agent, _knowledge = _orchestrator(
        (bundle,), intent_classifier=classifier
    )

    _, outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What is the flood outlook?", village_name="Mingora"),
        )
    )

    assert len(runtime.inputs) == 1
    assert outcome.response_type is ConversationResponseType.FLOOD_DECISION


def test_classifier_failure_falls_back_to_knowledge_tool_in_policy_advisor_mode() -> None:
    """A classifier outage must never block or misroute a policy-advisor turn."""
    classifier = _IntentClassifierSpy(error=IntentClassificationError("boom"))
    orchestrator, runtime, agent, knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    _, outcome = asyncio.run(
        orchestrator.handle_turn(
            None,
            UserRequest(request_text="What does government policy require?"),
            mode=ConversationMode.POLICY_ADVISOR,
        )
    )

    assert knowledge.questions == ["What does government policy require?"]
    assert outcome.response_type is ConversationResponseType.POLICY_ANSWER


def test_classifier_failure_still_requires_location_for_flood_agent() -> None:
    """A classifier outage must not bypass the existing location requirement."""
    classifier = _IntentClassifierSpy(error=IntentClassificationError("boom"))
    orchestrator, runtime, agent, _knowledge = _orchestrator(
        (), intent_classifier=classifier
    )

    with pytest.raises(MissingLocationError):
        asyncio.run(
            orchestrator.handle_turn(
                None, UserRequest(request_text="What is the flood outlook?")
            )
        )

    assert not runtime.inputs
