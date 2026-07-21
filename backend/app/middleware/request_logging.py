"""Request logging middleware."""

from time import perf_counter
from uuid import uuid4

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

from backend.app.core.logger import get_logger


logger = get_logger(__name__)


async def log_request(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Log request completion, timing, and unhandled middleware errors.

    Args:
        request: The incoming HTTP request.
        call_next: The middleware callable that processes the request.

    Returns:
        The response returned by the next middleware or route handler.

    Raises:
        Exception: Re-raises an unhandled request processing error after logging it.
    """

    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    start_time = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed: method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed: method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - start_time) * 1000,
        request_id,
    )
    return response
