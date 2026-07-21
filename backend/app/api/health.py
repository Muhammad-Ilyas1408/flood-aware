"""Health-check API endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from backend.app.config.settings import Settings, get_settings
from backend.app.core.logger import get_logger
from backend.app.schemas.health import HealthResponse


logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check application health",
)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return the service health and basic deployment metadata."""

    logger.debug("Health check requested.")
    return HealthResponse(
        status="healthy",
        application=settings.application_name,
        version=settings.version,
        environment=settings.environment.value,
        timestamp=datetime.now(UTC),
    )
