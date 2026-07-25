"""Village dataset API endpoint."""

from fastapi import APIRouter, Depends, status

from backend.app.composition import get_village_use_case
from backend.app.schemas.datasets import VillageListResponse
from backend.app.schemas.errors import ErrorResponse
from backend.app.use_cases.protocols import ViewVillagesUseCaseProtocol

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
    use_case: ViewVillagesUseCaseProtocol = Depends(get_village_use_case),
) -> VillageListResponse:
    """Return configured village records translated from the use-case DTO."""
    return VillageListResponse.from_dto(use_case.execute())
