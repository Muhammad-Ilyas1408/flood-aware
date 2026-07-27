"""Map canonical LLM decisions into graph-owned recommendation evidence."""

from backend.app.decision.models import Decision
from backend.app.graph.state import RecommendationEvidence


class DecisionRecommendationMapper:
    """Project validated decisions into graph evidence without provider coupling.

    This mapper performs no provider calls, parsing, or additional reasoning.
    """

    @staticmethod
    def to_graph(decision: Decision) -> RecommendationEvidence:
        """Return graph recommendation evidence derived only from the decision."""
        return RecommendationEvidence(
            recommendation=decision.recommendation.summary,
            rationale=" ".join(reason.statement for reason in decision.reasons) or None,
            risk_level=decision.risk_assessment.level.value,
            confidence=_confidence_value(decision.confidence.value),
            recommended_actions=tuple(
                action.action for action in decision.recommendation.actions
            ),
            citations=decision.recommendation.citations,
            evacuation_priority=_first_action_priority(decision),
            supporting_evidence=decision.recommendation.supporting_evidence,
            missing_evidence=decision.recommendation.missing_evidence,
        )


def _confidence_value(value: str) -> float:
    """Map the bounded decision-confidence vocabulary to graph confidence."""
    return {"low": 0.33, "medium": 0.66, "high": 1.0}[value]


def _first_action_priority(decision: Decision) -> str | None:
    """Preserve the first LLM-declared action priority without ranking actions."""
    if not decision.recommendation.actions:
        return None
    return decision.recommendation.actions[0].priority.value
