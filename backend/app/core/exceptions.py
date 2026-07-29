"""Centralized HTTP exception handling for the FastAPI application."""

from datetime import UTC, datetime

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.app.conversation.exceptions import ConversationSessionNotFoundError
from backend.app.core.application_exceptions import ApplicationError
from backend.app.core.logger import get_logger
from backend.app.core.validation_exceptions import ValidationException
from backend.app.decision.exceptions import DecisionGenerationError
from backend.app.schemas.errors import ErrorResponse, ValidationIssue

logger = get_logger(__name__)


def _error_response(
    request: Request,
    status_code: int,
    detail: str,
    errors: list[ValidationIssue] | None = None,
) -> JSONResponse:
    """Build a standardized JSON error response without exposing internals."""

    payload = ErrorResponse(
        status_code=status_code,
        detail=detail,
        path=request.url.path,
        request_id=getattr(request.state, "request_id", None),
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
    detail = (
        exception.detail if isinstance(exception.detail, str) else "Request failed."
    )
    return _error_response(request, exception.status_code, detail)


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
        request,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Request validation failed.",
        [
            ValidationIssue(
                location=[
                    str(part) if not isinstance(part, int) else part
                    for part in error["loc"]
                ],
                message=error["msg"],
                error_type=error["type"],
            )
            for error in exception.errors()
        ],
    )


async def handle_validation_exception(
    request: Request,
    exception: ValidationException,
) -> JSONResponse:
    """Return a consistent response for shared domain validation failures."""

    logger.warning(
        "Domain validation failed: method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exception).__name__,
    )
    return _error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Request validation failed.",
        [
            ValidationIssue(
                location=[exception.field] if exception.field else ["validation"],
                message=exception.message,
                error_type=type(exception).__name__,
            )
        ],
    )


async def handle_application_exception(
    request: Request,
    exception: ApplicationError,
) -> JSONResponse:
    """Return a safe standardized response for known application failures."""

    logger.error(
        "Application exception: method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exception).__name__,
    )
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected server error occurred.",
    )


async def handle_decision_generation_error(
    request: Request,
    exception: DecisionGenerationError,
) -> JSONResponse:
    """Return a safe standardized response for decision-generation failures."""

    logger.error(
        "Decision generation exception: method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exception).__name__,
    )
    return _error_response(
        request,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The recommendation service is temporarily unavailable. Please try again.",
    )


async def handle_conversation_session_not_found_error(
    request: Request,
    exception: ConversationSessionNotFoundError,
) -> JSONResponse:
    """Return a safe standardized response for an unknown conversation session."""

    logger.error(
        "Conversation session not found: method=%s path=%s exception_type=%s",
        request.method,
        request.url.path,
        type(exception).__name__,
    )
    return _error_response(
        request,
        status.HTTP_404_NOT_FOUND,
        "The requested conversation session was not found. Start a new conversation.",
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
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected server error occurred.",
    )
