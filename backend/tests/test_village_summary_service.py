"""Focused unit tests for the lightweight VillageSummaryService."""

from datetime import UTC, datetime

import pytest

from backend.app.flood.classification.exceptions import FloodClassificationError
from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.forecast.exceptions import ForecastSnapshotNotFoundError
from backend.app.forecast.models import ForecastResult
from backend.app.models.enums import FloodSeverity
from backend.app.village_summary.service import VillageSummaryService
from backend.app.weather.exceptions import WeatherClientError
from backend.app.weather.models import WeatherRequest, WeatherResult
from backend.tests.graph_test_support import forecast_result

_CLOCK_NOW = datetime(2026, 7, 27, tzinfo=UTC)


def _weather_result(**overrides: object) -> WeatherResult:
    """Create a complete real weather result without external I/O."""
    defaults: dict[str, object] = {
        "location": "Mingora",
        "country": "PK",
        "latitude": 34.75,
        "longitude": 72.35,
        "temperature": 28.5,
        "feels_like": 29.0,
        "humidity": 60,
        "pressure": 1010,
        "wind_speed": 2.5,
        "weather_condition": "Rain",
        "weather_description": "moderate rain",
        "rainfall": 3.0,
        "timestamp": _CLOCK_NOW,
        "source": "OpenWeatherMap",
    }
    defaults.update(overrides)
    return WeatherResult(**defaults)


class _FakeWeatherTool:
    """Return a scripted weather result or raise a scripted weather error."""

    def __init__(
        self,
        result: WeatherResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[WeatherRequest] = []

    def get_current_weather(self, request: WeatherRequest) -> WeatherResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _FakeForecastProvider:
    """Return a scripted forecast result or raise a scripted forecast error."""

    def __init__(
        self,
        result: ForecastResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[tuple[float, float]] = []

    def get_forecast(self, latitude: float, longitude: float) -> ForecastResult:
        self.calls.append((latitude, longitude))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _FailingClassificationService:
    """Always raise a classification failure for the classify boundary."""

    def classify(self, forecast: ForecastResult) -> FloodSeverity:
        raise FloodClassificationError("Simulated classification failure.")


def _classification_service() -> FloodClassificationService:
    """Build a real classifier with clear round-number discharge thresholds."""
    return FloodClassificationService(
        FloodClassificationPolicy(
            moderate_discharge=100.0,
            major_discharge=200.0,
            extreme_discharge=300.0,
        )
    )


def test_summarize_returns_full_data_when_weather_and_forecast_succeed() -> None:
    """A successful call reports real weather and a real classified severity."""
    weather_tool = _FakeWeatherTool(result=_weather_result())
    forecast_provider = _FakeForecastProvider(
        result=forecast_result(discharge_m3_per_second=150.0, retrieved_at=_CLOCK_NOW)
    )
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _classification_service(),
        max_snapshot_age_hours=48,
        clock=lambda: _CLOCK_NOW,
    )

    summary = service.summarize(
        name="Bishbanr", district="Swat", latitude=34.75, longitude=72.35
    )

    assert summary.name == "Bishbanr"
    assert summary.district == "Swat"
    assert summary.weather is not None
    assert summary.weather.temperature == 28.5
    assert summary.weather.weather_condition == "Rain"
    assert summary.weather_unavailable_reason is None
    assert summary.severity == FloodSeverity.MODERATE
    assert summary.severity_unavailable_reason is None
    assert summary.forecast_stale is False
    assert summary.status_message == "Stay alert, monitor forecasts"
    assert weather_tool.calls == [WeatherRequest(latitude=34.75, longitude=72.35)]
    assert forecast_provider.calls == [(34.75, 72.35)]


def test_summarize_reports_weather_unavailable_without_losing_severity() -> None:
    """A weather-tool failure is reported honestly without discarding severity."""
    weather_tool = _FakeWeatherTool(error=WeatherClientError("provider unreachable"))
    forecast_provider = _FakeForecastProvider(
        result=forecast_result(discharge_m3_per_second=50.0, retrieved_at=_CLOCK_NOW)
    )
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _classification_service(),
        max_snapshot_age_hours=48,
        clock=lambda: _CLOCK_NOW,
    )

    summary = service.summarize(
        name="Kas", district="Swat", latitude=34.74, longitude=72.34
    )

    assert summary.weather is None
    assert summary.weather_unavailable_reason == (
        "Current weather is temporarily unavailable."
    )
    assert summary.severity == FloodSeverity.MINOR
    assert summary.severity_unavailable_reason is None


def test_summarize_reports_severity_unavailable_without_losing_weather() -> None:
    """A forecast-provider failure is reported honestly without fabricating severity."""
    weather_tool = _FakeWeatherTool(result=_weather_result())
    forecast_provider = _FakeForecastProvider(
        error=ForecastSnapshotNotFoundError("no local snapshot")
    )
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _classification_service(),
        max_snapshot_age_hours=48,
    )

    summary = service.summarize(
        name="Kozqila", district="Swat", latitude=34.73, longitude=72.33
    )

    assert summary.weather is not None
    assert summary.weather_unavailable_reason is None
    assert summary.severity is None
    assert summary.severity_unavailable_reason == (
        "No local flood forecast is available for this location."
    )
    assert summary.forecast_stale is None
    assert summary.status_message == "Insufficient data to assess flood risk"


def test_summarize_reports_classification_failure_without_fabricating_severity() -> None:
    """A classification failure is reported honestly, never guessed."""
    weather_tool = _FakeWeatherTool(result=_weather_result())
    forecast_provider = _FakeForecastProvider(result=forecast_result())
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _FailingClassificationService(),
        max_snapshot_age_hours=48,
        clock=lambda: _CLOCK_NOW,
    )

    summary = service.summarize(
        name="Ashargarai", district="Swat", latitude=34.76, longitude=72.36
    )

    assert summary.severity is None
    assert summary.severity_unavailable_reason == (
        "The flood forecast could not be classified."
    )
    assert summary.status_message == "Insufficient data to assess flood risk"


def test_summarize_flags_stale_forecast_snapshot() -> None:
    """A snapshot older than the configured threshold is flagged, not hidden."""
    weather_tool = _FakeWeatherTool(result=_weather_result())
    forecast_provider = _FakeForecastProvider(
        result=forecast_result(
            discharge_m3_per_second=50.0,
            retrieved_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
    )
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _classification_service(),
        max_snapshot_age_hours=48,
        clock=lambda: _CLOCK_NOW,
    )

    summary = service.summarize(
        name="Jambil", district="Swat", latitude=34.77, longitude=72.37
    )

    assert summary.severity is not None
    assert summary.forecast_stale is True


@pytest.mark.parametrize(
    ("discharge", "expected_severity", "expected_message"),
    [
        (50.0, FloodSeverity.MINOR, "Monitor conditions"),
        (150.0, FloodSeverity.MODERATE, "Stay alert, monitor forecasts"),
        (250.0, FloodSeverity.MAJOR, "Consider evacuation preparations"),
        (350.0, FloodSeverity.EXTREME, "Consider evacuation preparations"),
    ],
)
def test_summarize_maps_each_severity_tier_to_its_status_message(
    discharge: float, expected_severity: FloodSeverity, expected_message: str
) -> None:
    """Every real severity tier maps to its documented deterministic message."""
    weather_tool = _FakeWeatherTool(result=_weather_result())
    forecast_provider = _FakeForecastProvider(
        result=forecast_result(discharge_m3_per_second=discharge, retrieved_at=_CLOCK_NOW)
    )
    service = VillageSummaryService(
        weather_tool,
        forecast_provider,
        _classification_service(),
        max_snapshot_age_hours=48,
        clock=lambda: _CLOCK_NOW,
    )

    summary = service.summarize(
        name="Manglawar", district="Swat", latitude=34.79, longitude=72.39
    )

    assert summary.severity == expected_severity
    assert summary.status_message == expected_message
