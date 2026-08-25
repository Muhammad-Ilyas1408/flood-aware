"""Lightweight, non-LLM village condition summary service.

Computes real current weather and a real deterministic flood-severity
classification for one coordinate, using the same production Weather Tool
and ``FloodClassificationService`` the graph uses, without invoking GIS
analysis or the LangGraph/OpenAI decision agent. Severity is derived from
the forecast alone -- exactly what
``backend.app.graph.router.flood_severity_policy.FloodSeverityRoutingPolicy``
already relies on to route the graph before any GIS step runs -- so this is
a strict subset of existing evidence, not a second, parallel classification.
"""

from datetime import UTC, datetime

from backend.app.flood.classification.exceptions import FloodClassificationError
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.forecast.exceptions import ForecastError
from backend.app.gis.domain.protocols import ForecastProvider
from backend.app.models.enums import FloodSeverity
from backend.app.village_summary.models import VillageConditionSummary, WeatherSnapshot
from backend.app.village_summary.status_messages import status_message_for
from backend.app.weather.exceptions import WeatherError
from backend.app.weather.models import WeatherRequest
from backend.app.weather.weather_tool import WeatherTool


class VillageSummaryService:
    """Compose current weather and forecast-derived severity into one summary."""

    def __init__(
        self,
        weather_tool: WeatherTool,
        forecast_provider: ForecastProvider,
        classification_service: FloodClassificationService,
        *,
        max_snapshot_age_hours: int,
    ) -> None:
        """Initialize the service with its injected production boundaries.

        Args:
            weather_tool: The production current-weather boundary.
            forecast_provider: The production local-snapshot GloFAS forecast boundary.
            classification_service: The canonical forecast-severity classifier.
            max_snapshot_age_hours: The threshold past which a forecast snapshot
                is honestly flagged stale rather than presented as fresh.
        """

        self._weather_tool = weather_tool
        self._forecast_provider = forecast_provider
        self._classification_service = classification_service
        self._max_snapshot_age_hours = max_snapshot_age_hours

    def summarize(
        self, *, name: str, district: str, latitude: float, longitude: float
    ) -> VillageConditionSummary:
        """Return one honest condition summary for a single village location."""
        weather, weather_unavailable_reason = self._current_weather(latitude, longitude)
        severity, forecast_stale, severity_unavailable_reason = self._severity(
            latitude, longitude
        )
        return VillageConditionSummary(
            name=name,
            district=district,
            latitude=latitude,
            longitude=longitude,
            weather=weather,
            weather_unavailable_reason=weather_unavailable_reason,
            severity=severity,
            severity_unavailable_reason=severity_unavailable_reason,
            forecast_stale=forecast_stale,
            status_message=status_message_for(severity),
        )

    def _current_weather(
        self, latitude: float, longitude: float
    ) -> tuple[WeatherSnapshot | None, str | None]:
        """Return a mapped weather snapshot, or an honest unavailability reason."""
        try:
            result = self._weather_tool.get_current_weather(
                WeatherRequest(latitude=latitude, longitude=longitude)
            )
        except WeatherError:
            return None, "Current weather is temporarily unavailable."
        return (
            WeatherSnapshot(
                temperature=result.temperature,
                weather_condition=result.weather_condition,
                weather_description=result.weather_description,
                humidity=result.humidity,
                rainfall=result.rainfall,
                observed_at=result.timestamp,
            ),
            None,
        )

    def _severity(
        self, latitude: float, longitude: float
    ) -> tuple[FloodSeverity | None, bool | None, str | None]:
        """Return classified severity and snapshot staleness, or an honest reason."""
        try:
            forecast = self._forecast_provider.get_forecast(latitude, longitude)
        except ForecastError:
            return None, None, "No local flood forecast is available for this location."
        try:
            severity = self._classification_service.classify(forecast)
        except FloodClassificationError:
            return None, None, "The flood forecast could not be classified."
        age_hours = max(
            0.0,
            (datetime.now(UTC) - forecast.metadata.retrieved_at).total_seconds() / 3600,
        )
        return severity, age_hours > self._max_snapshot_age_hours, None
