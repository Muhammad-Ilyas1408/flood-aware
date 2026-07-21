"""Centralized HTTP exception handling for the FastAPI application."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from backend.app.core.logger import get_logger


logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Represent the standardized JSON error response returned by the API."""

    status_code: int
    detail: str
    timestamp: datetime
    errors: list[dict[str, Any]] | None = None


def _error_response(
    status_code: int,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Build a standardized JSON error response without exposing internals."""

    payload = ErrorResponse(
        status_code=status_code,
        detail=detail,
        timestamp=datetime.now(UTC),
        errors=errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload.model_dump(mode="json", exclude_none=True)),
    )


async def handle_http_exception(
    request: Request,
    exception: HTTPException,
) -> JSONResponse:
    """Return a consistent response for expected HTTP exceptions."""

    logger.warning(
        "HTTP exception: method=%s path=%s status_code=%s",
        request.method,
        request.url.path,
        exception.status_code,
    )
    detail = exception.detail if isinstance(exception.detail, str) else "Request failed."
    return _error_response(exception.status_code, detail)


async def handle_request_validation_error(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """Return a consistent response for request validation failures."""

    logger.warning(
        "Request validation failed: method=%s path=%s error_count=%s",
        request.method,
        request.url.path,
        len(exception.errors()),
    )
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Request validation failed.",
        exception.errors(),
    )


async def handle_unexpected_exception(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """Log unexpected exceptions and return a safe generic error response."""

    logger.exception(
        "Unhandled exception: method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exception).__name__,
    )
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected server error occurred.",
    )
