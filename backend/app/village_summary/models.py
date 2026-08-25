"""Immutable domain models for lightweight village condition summaries."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import FloodSeverity


class WeatherSnapshot(BaseModel):
    """Immutable current-weather snapshot for one village condition summary."""

    model_config = ConfigDict(frozen=True)

    temperature: float
    weather_condition: str
    weather_description: str
    humidity: int = Field(ge=0, le=100)
    rainfall: float | None = Field(default=None, ge=0)
    observed_at: datetime


class VillageConditionSummary(BaseModel):
    """Represent one village's honestly-graded, lightweight flood condition.

    Weather and severity are independent pieces of evidence: either may be
    unavailable without invalidating the other. A ``None`` severity means
    the forecast could not be classified -- it is never fabricated from
    incomplete evidence.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    district: str
    latitude: float
    longitude: float
    weather: WeatherSnapshot | None
    weather_unavailable_reason: str | None
    severity: FloodSeverity | None
    severity_unavailable_reason: str | None
    forecast_stale: bool | None
    status_message: str
