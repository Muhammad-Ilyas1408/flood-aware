"""Immutable domain models representing parsed GloFAS discharge forecasts."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.gis.geometry import DistanceResult, Point


class ForecastLocation(BaseModel):
    """Preserve requested and selected GloFAS grid locations with their distance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_point: Point
    grid_point: Point
    grid_distance: DistanceResult


class ForecastMetadata(BaseModel):
    """Describe the provenance shared by every point in one forecast result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_path: Path
    dataset_name: str = Field(min_length=1)
    product_type: str = Field(min_length=1)
    hydrological_model: str = Field(min_length=1)
    system_version: str = Field(min_length=1)
    forecast_reference_time: datetime
    retrieved_at: datetime

    @model_validator(mode="after")
    def validate_utc_timestamps(self) -> "ForecastMetadata":
        """Require timezone-aware provenance timestamps."""

        if self.forecast_reference_time.tzinfo is None:
            raise ValueError("forecast_reference_time must be timezone-aware.")
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware.")
        return self


class ForecastPoint(BaseModel):
    """Represent one modelled river-discharge value at a forecast valid time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid_time: datetime
    lead_time_hours: int = Field(ge=0)
    discharge_m3_per_second: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_timezone(self) -> "ForecastPoint":
        """Require a timezone-aware valid time."""

        if self.valid_time.tzinfo is None:
            raise ValueError("valid_time must be timezone-aware.")
        return self


class ForecastSeries(BaseModel):
    """Store chronologically ordered discharge values for one selected grid cell."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    points: tuple[ForecastPoint, ...]

    @model_validator(mode="after")
    def validate_points(self) -> "ForecastSeries":
        """Require a non-empty series with strictly increasing valid times."""

        if not self.points:
            raise ValueError("Forecast series must contain at least one point.")
        valid_times = tuple(point.valid_time for point in self.points)
        if valid_times != tuple(sorted(valid_times)):
            raise ValueError("Forecast points must be ordered by valid_time.")
        if len(set(valid_times)) != len(valid_times):
            raise ValueError("Forecast points must not share a valid_time.")
        return self


class ForecastResult(BaseModel):
    """Expose validated local GloFAS forecast data without flood interpretation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    location: ForecastLocation
    metadata: ForecastMetadata
    series: ForecastSeries
