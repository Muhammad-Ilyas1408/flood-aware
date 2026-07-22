"""Village dataset API endpoint."""

from fastapi import APIRouter, Depends, status

from backend.app.composition import get_village_service
from backend.app.schemas.datasets import VillageListResponse
from backend.app.schemas.errors import ErrorResponse
from backend.app.services.protocols import VillageServiceProtocol


router = APIRouter(tags=["Villages"])


@router.get(
    "/villages",
    response_model=VillageListResponse,
    status_code=status.HTTP_200_OK,
    summary="List configured villages",
    description="Return the complete configured village dataset.",
    operation_id="getVillages",
    responses={
        status.HTTP_200_OK: {"description": "Configured village records returned."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "The application could not complete the request.",
        },
    },
)
def get_villages(
    service: VillageServiceProtocol = Depends(get_village_service),
) -> VillageListResponse:
    """Return configured village records translated from the service DTO."""
    return VillageListResponse.from_dto(service.load_villages())
