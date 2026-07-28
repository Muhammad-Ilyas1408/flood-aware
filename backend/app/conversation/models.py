"""Immutable conversation contracts for grounded multi-turn decisions."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from backend.app.decision.models import Decision
from backend.app.graph.state import Coordinate, EvidenceBundle


class _FrozenConversationModel(BaseModel):
    """Provide strict immutable behavior for conversation domain state."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ConversationTurn(_FrozenConversationModel):
    """Record one request, its active evidence, and its grounded decision."""

    request_text: str
    coordinates: Coordinate | None = None
    village_name: str | None = None
    district: str | None = None
    province: str | None = None
    evidence_bundle: EvidenceBundle
    decision: Decision
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
        """Expose the compact prior decision content needed for prompt history."""
        return self.decision.recommendation.summary


class ConversationSession(_FrozenConversationModel):
    """Store the ordered immutable turn history for one conversation."""

    session_id: UUID
    turns: tuple[ConversationTurn, ...] = ()
