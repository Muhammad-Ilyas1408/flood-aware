"""Standardized API error response schemas."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ResponseStatus
from backend.app.schemas.common import TimestampModel


class ValidationIssue(BaseModel):
    """Describe one field-level validation failure without exposing internals."""

    model_config = ConfigDict(extra="forbid")

    location: list[str | int] = Field(min_length=1)
    message: str = Field(min_length=1)
    error_type: str = Field(min_length=1, max_length=128)


class ErrorResponse(TimestampModel):
    """Represent the standardized error structure used by all API failures."""

    status: ResponseStatus = ResponseStatus.ERROR
    status_code: int = Field(ge=400, le=599)
    detail: str = Field(min_length=1, max_length=1_000)
    path: str = Field(min_length=1, max_length=2_048)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    errors: list[ValidationIssue] | None = None
