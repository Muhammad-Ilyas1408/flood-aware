"""Domain data contracts for flood decision support."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.models.enums import FloodSeverity, FloodStatus, RiskLevel
from backend.app.utils.validators import (
    validate_coordinates,
    validate_date_range,
    validate_identifier,
)


class Coordinates(BaseModel):
    """Represent a geographic point using WGS 84 latitude and longitude."""

    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float

    @model_validator(mode="after")
    def validate_point(self) -> "Coordinates":
        """Validate that the coordinate pair is within valid geographic bounds."""

        validate_coordinates(self.latitude, self.longitude)
        return self


class LocationReference(BaseModel):
    """Identify a location relevant to a flood assessment."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    coordinates: Coordinates
    administrative_area: str | None = Field(default=None, min_length=1, max_length=255)
    reference_id: str | None = Field(default=None, max_length=128)

    @field_validator("reference_id")
    @classmethod
    def validate_reference_id(cls, value: str | None) -> str | None:
        """Validate an optional stable reference identifier."""

        return validate_identifier(value) if value is not None else None


class AffectedPopulation(BaseModel):
    """Describe a population exposure estimate for one location."""

    model_config = ConfigDict(extra="forbid")

    location: LocationReference
    estimated_count: int = Field(ge=0)
    assessed_at: datetime


class ForecastSummary(BaseModel):
    """Describe future forecast output without implementing forecast generation."""

    model_config = ConfigDict(extra="forbid")

    location: LocationReference
    forecast_start: date
    forecast_end: date
    status: FloodStatus
    severity: FloodSeverity
    risk_level: RiskLevel
    generated_at: datetime

    @model_validator(mode="after")
    def validate_forecast_period(self) -> "ForecastSummary":
        """Validate that the forecast end date is not before its start date."""

        validate_date_range(self.forecast_start, self.forecast_end)
        return self
