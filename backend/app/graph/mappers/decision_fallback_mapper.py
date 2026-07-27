"""Map deterministic decision-provider failures into graph recommendation evidence."""

from backend.app.graph.state import RecommendationEvidence


class DecisionFallbackMapper:
    """Create the stable no-decision recommendation without reasoning or ranking."""

    @staticmethod
    def unavailable() -> RecommendationEvidence:
        """Return deterministic recommendation evidence for a provider failure."""
        return RecommendationEvidence(
            recommendation="Decision generation unavailable.",
            rationale="Provider temporarily unavailable.",
            risk_level="unknown",
            confidence=0.0,
            recommended_actions=(),
        )
