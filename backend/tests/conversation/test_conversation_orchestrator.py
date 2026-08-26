"""Focused multi-turn orchestration tests without graph tools or provider I/O."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from backend.app.conversation.exceptions import MissingLocationError
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
