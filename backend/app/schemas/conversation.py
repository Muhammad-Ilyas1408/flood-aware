"""API request/response contracts for grounded conversation turns."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.decision.models import (
    ActionRecommendation,
    Decision,
    DecisionConfidence,
    Priority,
    RiskLevel,
)
from backend.app.graph.state import Coordinate, UserRequest
from backend.app.models.enums import ResponseStatus
from backend.app.schemas.common import BaseResponse


class ConversationRequest(BaseModel):
    """Describe one inbound conversation turn request from an API client.

    Strict mode is deliberately not used here: this is an inbound schema
    parsed from arbitrary client JSON, and JSON has no native UUID type, so
    a strict ``session_id: UUID`` field would reject every real client's
    request (a syntactically valid UUID string is only accepted by
    Pydantic's lax coercion, never in strict mode). Response schemas remain
    strict because they are always constructed internally from
    already-typed domain objects, never parsed from external input.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID | None = None
    request_text: str = Field(min_length=1)
    coordinates: Coordinate | None = None
    village_name: str | None = None
    district: str | None = None
    province: str | None = None

    def to_user_request(self) -> UserRequest:
        """Translate this API request into the canonical graph user request."""
        return UserRequest(
            request_text=self.request_text,
            coordinates=self.coordinates,
            village_name=self.village_name,
            district=self.district,
            province=self.province,
        )


class ActionResponse(BaseModel):
    """Describe one recommended action returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action: str = Field(min_length=1)
    priority: Priority

    @classmethod
    def from_decision_action(
        cls, action: ActionRecommendation
    ) -> "ActionResponse":
        """Translate one canonical action recommendation into an API response model."""
        return cls(action=action.action, priority=action.priority)


class ConversationResponse(BaseResponse):
    """Describe the minimal public decision surface for one conversation turn.

    This intentionally excludes internal fields such as the full evidence
    bundle, conversation history, or grounding-only detail (reasons,
    supporting_evidence) that a client does not need to act on a decision.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: ResponseStatus = ResponseStatus.SUCCESS
    session_id: UUID
    risk_level: RiskLevel
    confidence: DecisionConfidence
    summary: str = Field(min_length=1)
    actions: tuple[ActionResponse, ...] = ()
    citations: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()

    @classmethod
    def from_decision(
        cls, session_id: UUID, decision: Decision
    ) -> "ConversationResponse":
        """Translate a canonical Decision into the minimal public API surface."""
        return cls(
            session_id=session_id,
            risk_level=decision.risk_assessment.level,
            confidence=decision.confidence,
            summary=decision.recommendation.summary,
            actions=tuple(
                ActionResponse.from_decision_action(action)
                for action in decision.recommendation.actions
            ),
            citations=decision.recommendation.citations,
            missing_evidence=decision.recommendation.missing_evidence,
        )
