"""API response contracts for lightweight village condition summaries."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.dtos.village_summary import VillageSummaryResultDTO
from backend.app.models.enums import FloodSeverity, ResponseStatus
from backend.app.schemas.common import BaseResponse
from backend.app.village_summary.models import VillageConditionSummary, WeatherSnapshot


class WeatherSnapshotResponse(BaseModel):
    """Describe one current-weather snapshot returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    temperature: float
    weather_condition: str = Field(min_length=1)
    weather_description: str = Field(min_length=1)
    humidity: int = Field(ge=0, le=100)
    rainfall: float | None = Field(default=None, ge=0)
    observed_at: datetime

    @classmethod
    def from_domain(cls, snapshot: WeatherSnapshot) -> "WeatherSnapshotResponse":
        """Translate a domain weather snapshot into an API response model."""
        return cls(
            temperature=snapshot.temperature,
            weather_condition=snapshot.weather_condition,
            weather_description=snapshot.weather_description,
            humidity=snapshot.humidity,
            rainfall=snapshot.rainfall,
            observed_at=snapshot.observed_at,
        )


class VillageConditionResponse(BaseModel):
    """Describe one village's lightweight, honestly-graded condition summary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    district: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    weather: WeatherSnapshotResponse | None
    weather_unavailable_reason: str | None
    severity: FloodSeverity | None
    severity_unavailable_reason: str | None
    forecast_stale: bool | None
    status_message: str = Field(min_length=1)

    @classmethod
    def from_domain(
        cls, summary: VillageConditionSummary
    ) -> "VillageConditionResponse":
        """Translate a domain village condition summary into an API response model."""
        return cls(
            name=summary.name,
            district=summary.district,
            latitude=summary.latitude,
            longitude=summary.longitude,
            weather=(
                WeatherSnapshotResponse.from_domain(summary.weather)
                if summary.weather is not None
                else None
            ),
            weather_unavailable_reason=summary.weather_unavailable_reason,
            severity=summary.severity,
            severity_unavailable_reason=summary.severity_unavailable_reason,
            forecast_stale=summary.forecast_stale,
            status_message=summary.status_message,
        )


class VillageSummaryListResponse(BaseResponse):
    """Describe a successful API response containing requested village summaries."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: ResponseStatus = ResponseStatus.SUCCESS
    data: tuple[VillageConditionResponse, ...]
    unknown_village_names: tuple[str, ...] = ()

    @classmethod
    def from_dto(cls, dto: VillageSummaryResultDTO) -> "VillageSummaryListResponse":
        """Translate an application village-summary DTO into an API response model."""
        return cls(
            data=tuple(
                VillageConditionResponse.from_domain(summary)
                for summary in dto.summaries
            ),
            unknown_village_names=dto.unknown_village_names,
        )
