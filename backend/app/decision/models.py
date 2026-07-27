"""Frozen canonical decision contracts for evidence-grounded AI reasoning."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class _FrozenDecisionModel(BaseModel):
    """Provide strict immutable decision-model behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RiskLevel(str, Enum):
    """Represent the overall factual risk level assessed from evidence."""

    NORMAL = "normal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class Priority(str, Enum):
    """Represent the operational priority of one recommended action."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionConfidence(str, Enum):
    """Represent the LLM's bounded confidence in evidence interpretation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionReason(_FrozenDecisionModel):
    """State one evidence-grounded reason supporting a decision."""

    statement: str = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()


class ActionRecommendation(_FrozenDecisionModel):
    """Describe one actionable recommendation with supporting evidence."""

    action: str = Field(min_length=1)
    priority: Priority
    evidence_references: tuple[str, ...] = ()


class RiskAssessment(_FrozenDecisionModel):
    """Describe the overall risk assessment without prescribing actions."""

    level: RiskLevel
    rationale: str = Field(min_length=1)


class Recommendation(_FrozenDecisionModel):
    """Represent an evidence-grounded recommendation for downstream consumers."""

    summary: str = Field(min_length=1)
    actions: tuple[ActionRecommendation, ...] = ()
    citations: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()


class Decision(_FrozenDecisionModel):
    """Represent the complete structured output of the LLM decision boundary."""

    risk_assessment: RiskAssessment
    recommendation: Recommendation
    reasons: tuple[DecisionReason, ...] = ()
    confidence: DecisionConfidence
