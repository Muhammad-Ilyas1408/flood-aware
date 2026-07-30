"""Focused multi-turn orchestration tests without graph tools or provider I/O."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import pytest

from backend.app.conversation.models import ConversationTurn
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
    EvidenceBundle,
    GraphState,
    KnowledgeEvidence,
    UserRequest,
)
from backend.app.observability.context import ExecutionContext


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
    orchestrator = ConversationOrchestrator(
        graph_runtime=runtime,
        decision_agent=agent,
        prompt_builder=PromptBuilder(),
        session_store=ConversationSessionStore(),
        state_factory=_state_factory(),
        clock=lambda: datetime(2026, 7, 28, tzinfo=UTC),
    )
    return orchestrator, runtime, agent


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
    orchestrator, runtime, agent = _orchestrator((first_bundle,))
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
    assert second.recommendation.summary == "decision-1"
    assert agent.calls[0][2] == "What about shelters?", (
        "The reuse-path decide() call must receive the CURRENT turn's own "
        "request text, not the prior turn's, so the model can actually see "
        "what this turn specifically asks about."
    )


def test_changed_village_runs_graph_again() -> None:
    """Changing the village must refresh the active evidence bundle."""
    first_bundle, second_bundle = _bundle("Mingora Plan"), _bundle("Saidu Plan")
    orchestrator, runtime, agent = _orchestrator((first_bundle, second_bundle))

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
    orchestrator, runtime, agent = _orchestrator((bundle,))
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
    orchestrator, runtime, agent = _orchestrator((first_bundle, second_bundle))
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
    orchestrator, _, agent = _orchestrator((first_bundle, second_bundle))
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
    orchestrator, runtime, agent = _orchestrator((bundle,), decisions=(None,))

    with pytest.raises(DecisionGenerationError):
        asyncio.run(
            orchestrator.handle_turn(
                None,
                UserRequest(request_text="Flood outlook?", village_name="Mingora"),
            )
        )

    assert len(runtime.inputs) == 1
    assert not agent.calls
