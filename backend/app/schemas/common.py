"""Reusable API response and metadata schemas."""

from typing import Generic, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from backend.app.models.enums import ResponseStatus

DataT = TypeVar("DataT")


class TimestampModel(BaseModel):
    """Provide an aware timestamp field for API contracts."""

    model_config = ConfigDict(extra="forbid")

    timestamp: AwareDatetime


class BaseMetadata(TimestampModel):
    """Describe metadata shared by API responses."""

    request_id: str | None = Field(default=None, min_length=1, max_length=128)


class BaseResponse(BaseModel):
    """Provide the status field shared by successful API responses."""

    model_config = ConfigDict(extra="forbid")

    status: ResponseStatus


class SuccessResponse(BaseResponse, Generic[DataT]):
    """Represent a successful API response carrying typed data."""

    status: ResponseStatus = ResponseStatus.SUCCESS
    data: DataT
    metadata: BaseMetadata | None = None


class MessageResponse(BaseResponse):
    """Represent a successful API response carrying a human-readable message."""

    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = Field(min_length=1, max_length=1_000)
    metadata: BaseMetadata | None = None


class PaginationMetadata(BaseMetadata):
    """Describe pagination details for a collection response."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(SuccessResponse[list[DataT]], Generic[DataT]):
    """Represent a successful paginated response carrying typed items."""

    pagination: PaginationMetadata
