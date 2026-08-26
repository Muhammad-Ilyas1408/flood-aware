"""Immutable conversation contracts for grounded multi-turn decisions."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from backend.app.decision.models import Decision
from backend.app.graph.state import Coordinate, EvidenceBundle


class _FrozenConversationModel(BaseModel):
    """Provide strict immutable behavior for conversation domain state."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ConversationMode(str, Enum):
    """Select which conversation behavior a request wants from the shared endpoint."""

    FLOOD_AGENT = "flood_agent"
    POLICY_ADVISOR = "policy_advisor"


class ConversationResponseType(str, Enum):
    """Discriminate what kind of outcome one conversation turn produced."""

    FLOOD_DECISION = "flood_decision"
    SMALL_TALK = "small_talk"
    POLICY_ANSWER = "policy_answer"
    CAPABILITY_QUESTION = "capability_question"
    NEEDS_CLARIFICATION = "needs_clarification"


class ConversationOutcome(_FrozenConversationModel):
    """Represent the result of one turn without forcing a flood-decision shape.

    ``decision`` is populated only for ``FLOOD_DECISION``; ``citations`` only for
    ``POLICY_ANSWER``. A small-talk reply carries neither, since it never
    collects evidence or invokes the decision agent.
    """

    response_type: ConversationResponseType
    summary: str
    decision: Decision | None = None
    citations: tuple[str, ...] = ()


class ConversationTurn(_FrozenConversationModel):
    """Record one request, its active evidence, and its outcome summary.

    ``decision`` is populated only when this turn ran the full flood-decision
    pipeline; small-talk and policy-advisor turns leave it ``None`` and rely on
    ``summary`` alone for prompt-history continuity.
    """

    request_text: str
    coordinates: Coordinate | None = None
    village_name: str | None = None
    district: str | None = None
    province: str | None = None
    evidence_bundle: EvidenceBundle
    decision: Decision | None = None
    summary: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_utc_timestamp(cls, value: datetime) -> datetime:
        """Require UTC timestamps for deterministic session ordering."""
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must be UTC")
        return value

    @property
    def recommendation_summary(self) -> str:
        """Expose the compact prior outcome content needed for prompt history."""
        return self.summary


class ConversationSession(_FrozenConversationModel):
    """Store the ordered immutable turn history for one conversation."""

    session_id: UUID
    turns: tuple[ConversationTurn, ...] = ()
