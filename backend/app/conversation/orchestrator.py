"""Thin multi-turn orchestration over immutable graph and decision boundaries."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from backend.app.conversation.evidence_reuse import requires_new_evidence
from backend.app.conversation.exceptions import (
    ConversationSessionNotFoundError,
    IntentClassificationError,
    MissingLocationError,
)
from backend.app.conversation.intent import (
    IntentClassification,
    IntentClassifierProtocol,
    IntentLabel,
)
from backend.app.conversation.models import (
    ConversationMode,
    ConversationOutcome,
    ConversationResponseType,
    ConversationTurn,
)
from backend.app.conversation.session_store import ConversationSessionStore
from backend.app.conversation.small_talk import is_small_talk, small_talk_reply
from backend.app.core.logger import get_logger
from backend.app.decision.exceptions import DecisionGenerationError
from backend.app.decision.prompt_builder import PromptBuilder
from backend.app.decision.protocols import DecisionAgentProtocol
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.mappers import KnowledgeEvidenceMapper
from backend.app.graph.runtime import GraphRuntime
from backend.app.graph.state import EvidenceBundle, GraphState, UserRequest
from backend.app.observability.context import ExecutionContext
from backend.app.observability.logging import log_event
from backend.app.rag.knowledge_tool import KnowledgeTool

_LOGGER = get_logger(__name__)


class ConversationOrchestrator:
    """Coordinate evidence reuse and grounded decisions without business logic.

    The orchestrator owns session sequencing only. Graph execution remains owned
    by ``GraphRuntime``; prompt construction and grounded decision generation
    remain owned by the injected decision-agent boundary.
    """

    def __init__(
        self,
        *,
        graph_runtime: GraphRuntime,
        decision_agent: DecisionAgentProtocol,
        prompt_builder: PromptBuilder,
        session_store: ConversationSessionStore,
        state_factory: GraphStateFactory,
        knowledge_tool: KnowledgeTool,
        intent_classifier: IntentClassifierProtocol,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize explicit conversation collaborators.

        ``prompt_builder`` remains explicitly composed with the agent boundary so
        the conversation composition root documents the prompt dependency without
        taking over prompt construction from the provider. ``knowledge_tool`` is
        injected directly (rather than only reached through the graph) so a
        policy-advisor turn can answer from government knowledge alone, without
        running the flood-evidence graph or the flood-decision agent.
        ``intent_classifier`` is consulted only for turns the deterministic
        small-talk check does not match, and only to decide whether to run the
        mode's existing heavy pipeline at all -- never to replace or relax it.
        """
        self._graph_runtime = graph_runtime
        self._decision_agent = decision_agent
        self._prompt_builder = prompt_builder
        self._session_store = session_store
        self._state_factory = state_factory
        self._knowledge_tool = knowledge_tool
        self._intent_classifier = intent_classifier
        self._clock = clock or (lambda: datetime.now(UTC))

    async def handle_turn(
        self,
        session_id: UUID | None,
        request: UserRequest,
        *,
        mode: ConversationMode = ConversationMode.FLOOD_AGENT,
    ) -> tuple[UUID, ConversationOutcome]:
        """Handle one turn, routing casual and policy-only turns off the flood pipeline."""
        resolved_session_id = session_id or await self._session_store.create_session()
        session = await self._session_store.get_session(resolved_session_id)
        if session is None:
            raise ConversationSessionNotFoundError(
                f"Conversation session {resolved_session_id} does not exist."
            )

        small_talk = is_small_talk(request.request_text)
        classification: IntentClassification | None = None
        if not small_talk:
            classification = await self._classify_intent(
                request.request_text,
                mode=mode,
                history=session.turns,
                has_location=_has_location(request),
            )

        if small_talk:
            outcome = ConversationOutcome(
                response_type=ConversationResponseType.SMALL_TALK,
                summary=small_talk_reply(request.request_text, mode),
            )
            evidence = EvidenceBundle()
        elif classification is not None and (
            classification.label is IntentLabel.CAPABILITY_QUESTION
        ):
            outcome = ConversationOutcome(
                response_type=ConversationResponseType.CAPABILITY_QUESTION,
                summary=classification.response_text,
            )
            evidence = EvidenceBundle()
        elif classification is not None and (
            classification.label is IntentLabel.NEEDS_CLARIFICATION
        ):
            outcome = ConversationOutcome(
                response_type=ConversationResponseType.NEEDS_CLARIFICATION,
                summary=classification.response_text,
            )
            evidence = EvidenceBundle()
        elif mode is ConversationMode.POLICY_ADVISOR:
            answer = await asyncio.to_thread(
                self._knowledge_tool.answer, request.request_text
            )
            knowledge_evidence = KnowledgeEvidenceMapper.to_graph(answer)
            outcome = ConversationOutcome(
                response_type=ConversationResponseType.POLICY_ANSWER,
                summary=answer.text,
                citations=knowledge_evidence.citations,
            )
            evidence = EvidenceBundle(knowledge=knowledge_evidence)
        else:
            if not _has_location(request):
                raise MissingLocationError(
                    "A village or coordinates are required to assess flood "
                    "risk.",
                    field="village_name",
                )
            previous = session.turns[-1] if session.turns else None
            state = self._state_for_request(request)
            if requires_new_evidence(_turn_request(previous), request):
                active_state = await self._graph_runtime.execute(state)
                evidence = active_state.evidence_bundle
                decision = active_state.decision
                if decision is None:
                    raise DecisionGenerationError(
                        "Graph execution completed without a canonical decision."
                    )
            else:
                evidence = previous.evidence_bundle
                decision = await self._decision_agent.decide(
                    evidence,
                    execution_context=ExecutionContext.from_graph_state(state),
                    history=session.turns,
                    current_request_text=request.request_text,
                )
            outcome = ConversationOutcome(
                response_type=ConversationResponseType.FLOOD_DECISION,
                summary=decision.recommendation.summary,
                decision=decision,
            )

        await self._session_store.append_turn(
            resolved_session_id,
            ConversationTurn(
                request_text=request.request_text,
                coordinates=request.coordinates,
                village_name=request.village_name,
                district=request.district,
                province=request.province,
                evidence_bundle=evidence,
                decision=outcome.decision,
                summary=outcome.summary,
                created_at=self._clock(),
            ),
        )
        return resolved_session_id, outcome

    async def _classify_intent(
        self,
        request_text: str,
        *,
        mode: ConversationMode,
        history: tuple[ConversationTurn, ...],
        has_location: bool,
    ) -> IntentClassification | None:
        """Classify one non-small-talk turn, or None if classification is unavailable.

        A ``None`` result must be treated exactly like ``GENUINE_QUESTION``:
        the caller falls through to the mode's existing default pipeline. A
        classifier outage must never drop, misroute, or silently reinterpret
        a genuine question -- it can only ever cost the speculative-pipeline
        behavior this feature exists to avoid, not correctness.

        ``has_location`` is the same structural fact ``_has_location`` checks
        before running the flood graph, computed once here and given to the
        classifier directly -- it must never be inferred from conversation
        text, which is an unreliable proxy for whether a location is
        actually resolved on the current request.
        """
        try:
            return await self._intent_classifier.classify(
                request_text, mode=mode, history=history, has_location=has_location
            )
        except IntentClassificationError:
            log_event(
                _LOGGER,
                logging.WARNING,
                "intent_classification_failed",
                ExecutionContext.uncorrelated(),
                mode=mode.value,
            )
            return None

    def _state_for_request(self, request: UserRequest) -> GraphState:
        """Create the canonical execution state without reconstructing request facts."""
        return self._state_factory.create(
            request_text=request.request_text,
            language=request.language,
            coordinates=request.coordinates,
            village_name=request.village_name,
            district=request.district,
            province=request.province,
            scenario_request=request.scenario_request,
        )


def _has_location(request: UserRequest) -> bool:
    """Return whether a request carries a coordinate or a real village name."""
    return request.coordinates is not None or bool(
        request.village_name and request.village_name.strip()
    )


def _turn_request(turn: ConversationTurn | None) -> UserRequest | None:
    """Project only the reuse-policy fields from one immutable conversation turn.

    Returns ``None`` -- treated identically to "no previous turn" by
    ``requires_new_evidence`` -- when the turn carried no real evidence.
    Small-talk, capability-question, and clarification outcomes always
    record an empty ``EvidenceBundle()``; reusing one just because its
    location happens to match the current turn would silently starve a
    genuine follow-up of all evidence, even though a real village or
    coordinates were present throughout.
    """
    if turn is None or turn.evidence_bundle == EvidenceBundle():
        return None
    return UserRequest(
        request_text=turn.request_text,
        coordinates=turn.coordinates,
        village_name=turn.village_name,
        district=turn.district,
        province=turn.province,
    )
