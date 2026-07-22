"""API response contracts for village, shelter, and dataset summary resources."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.data.models import DatasetMetadata, DatasetStatistics
from backend.app.models.enums import ResponseStatus
from backend.app.schemas.common import BaseResponse, SuccessResponse


class VillageResponse(BaseModel):
    """Describe one village record returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    district: str = Field(min_length=1)
    population: int = Field(ge=0)


class VillageListResponse(SuccessResponse[tuple[VillageResponse, ...]]):
    """Describe a successful API response containing ordered village records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ShelterResponse(BaseModel):
    """Describe one shelter record returned by the REST API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    district: str = Field(min_length=1)
    capacity: int = Field(ge=0)


class ShelterListResponse(SuccessResponse[tuple[ShelterResponse, ...]]):
    """Describe a successful API response containing ordered shelter records."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DatasetSummaryResponse(BaseResponse):
    """Describe lightweight dataset-level metadata and record statistics."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: ResponseStatus = ResponseStatus.SUCCESS
    metadata: DatasetMetadata
    statistics: DatasetStatistics
