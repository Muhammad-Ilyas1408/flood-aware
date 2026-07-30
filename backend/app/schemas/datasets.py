"""API response contracts for village, shelter, and dataset summary resources."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.data.models import DatasetMetadata, DatasetStatistics
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageDTO,
    VillageListDTO,
)
from backend.app.models.enums import ResponseStatus
from backend.app.schemas.common import BaseResponse, SuccessResponse


class VillageResponse(BaseModel):
    """Describe one village record returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    district: str = Field(min_length=1)
    population: int | None = Field(default=None, ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @classmethod
    def from_dto(cls, dto: VillageDTO) -> "VillageResponse":
        """Translate an application village DTO into an API response model."""
        return cls(
            name=dto.name,
            district=dto.district,
            population=dto.population,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )


class VillageListResponse(SuccessResponse[tuple[VillageResponse, ...]]):
    """Describe a successful API response containing ordered village records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dto(cls, dto: VillageListDTO) -> "VillageListResponse":
        """Translate an application village-list DTO into an API response model."""
        return cls(
            data=tuple(VillageResponse.from_dto(village) for village in dto.villages)
        )


class ShelterResponse(BaseModel):
    """Describe one shelter record returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    district: str = Field(min_length=1)
    capacity: int = Field(ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @classmethod
    def from_dto(cls, dto: ShelterDTO) -> "ShelterResponse":
        """Translate an application shelter DTO into an API response model."""
        return cls(
            name=dto.name,
            district=dto.district,
            capacity=dto.capacity,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )


class ShelterListResponse(SuccessResponse[tuple[ShelterResponse, ...]]):
    """Describe a successful API response containing ordered shelter records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dto(cls, dto: ShelterListDTO) -> "ShelterListResponse":
        """Translate an application shelter-list DTO into an API response model."""
        return cls(
            data=tuple(ShelterResponse.from_dto(shelter) for shelter in dto.shelters)
        )


class DatasetSummaryResponse(BaseResponse):
    """Describe lightweight dataset-level metadata and record statistics."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: ResponseStatus = ResponseStatus.SUCCESS
    metadata: DatasetMetadata
    statistics: DatasetStatistics

    @classmethod
    def from_dto(cls, dto: DatasetSummaryDTO) -> "DatasetSummaryResponse":
        """Translate an application dataset-summary DTO into an API response model."""
        return cls(metadata=dto.metadata, statistics=dto.statistics)


class DatasetCatalogResponse(BaseResponse):
    """Describe independent village and shelter dataset summaries for the API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: ResponseStatus = ResponseStatus.SUCCESS
    villages: DatasetSummaryResponse
    shelters: DatasetSummaryResponse

    @classmethod
    def from_dto(cls, dto: DatasetCatalogDTO) -> "DatasetCatalogResponse":
        """Translate an application dataset-catalog DTO into an API response model."""
        return cls(
            villages=DatasetSummaryResponse.from_dto(dto.villages),
            shelters=DatasetSummaryResponse.from_dto(dto.shelters),
        )
