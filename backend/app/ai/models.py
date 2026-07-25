"""Immutable domain language contracts for the Flood-Aware AI layer."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DecisionRequest",
    "DecisionContext",
    "Evidence",
    "RecommendationPriority",
    "Recommendation",
    "ToolResult",
    "DecisionResult",
]


class RecommendationPriority(str, Enum):
    """Classify the urgency of a stored recommendation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """Represent a request for decision-support information."""

    question: str
    scenario: str | None = None
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class Evidence:
    """Represent one independent piece of tool-produced decision evidence."""

    tool_name: str
    summary: str
    confidence: float | None = None
    data: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Represent a stored decision recommendation without generating it."""

    summary: str
    reasoning: str | None = None
    priority: RecommendationPriority | None = None
    actions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Represent the generic output returned by one AI tool."""

    tool_name: str
    summary: str
    data: object | None = None
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Represent information collected before producing a decision."""

    tool_results: tuple[ToolResult, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    notes: tuple[str, ...] = ()
    context: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Represent the complete decision-engine output for downstream consumers."""

    context: DecisionContext
    recommendations: tuple[Recommendation, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
