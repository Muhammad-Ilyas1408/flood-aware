"""Deterministic graph routing based on canonical flood evidence."""

from backend.app.flood.classification.service import FloodClassificationService
from backend.app.graph.state import GraphState
from backend.app.models.enums import FloodSeverity


class FloodSeverityRoutingPolicy:
    """Select graph paths from already-owned forecast and GIS facts.

    The policy does not mutate state or perform flood classification itself. It
    delegates classification to the established domain service and maps the
    resulting severity to the graph's fixed node identifiers.
    """

    _GIS_SEVERITIES = frozenset(
        (FloodSeverity.MODERATE, FloodSeverity.MAJOR, FloodSeverity.EXTREME)
    )
    _COMMUNITY_ANALYSIS_SEVERITIES = frozenset(
        (FloodSeverity.MAJOR, FloodSeverity.EXTREME)
    )

    def __init__(self, classification_service: FloodClassificationService) -> None:
        """Initialize the policy with the canonical classification boundary."""
        self._classification_service = classification_service

    def route_after_forecast(self, state: GraphState) -> str:
        """Choose GIS only for an elevated canonical forecast.

        A missing forecast is treated as unavailable evidence, so the graph
        continues directly to knowledge collection without attempting GIS.
        """
        forecast = state.forecast_result
        if forecast is None:
            return "knowledge"
        severity = self._classification_service.classify(forecast)
        return "gis" if severity in self._GIS_SEVERITIES else "knowledge"

    def route_after_gis(self, state: GraphState) -> str:
        """Choose community-impact analysis only for major flood evidence."""
        severity = self._gis_severity(state)
        return (
            "village"
            if severity in self._COMMUNITY_ANALYSIS_SEVERITIES
            else "knowledge"
        )

    @staticmethod
    def _gis_severity(state: GraphState) -> FloodSeverity | None:
        """Read the existing GIS evidence without deriving or changing facts."""
        value = state.gis.flood_zone
        if value is None:
            return None
        try:
            return FloodSeverity(value)
        except ValueError:
            return None
