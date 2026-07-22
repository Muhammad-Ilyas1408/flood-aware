"""Shelter dataset API endpoint."""

from fastapi import APIRouter, Depends, status

from backend.app.composition import get_shelter_use_case
from backend.app.schemas.datasets import ShelterListResponse
from backend.app.schemas.errors import ErrorResponse
from backend.app.use_cases.protocols import ViewSheltersUseCaseProtocol


router = APIRouter(tags=["Shelters"])


@router.get(
    "/shelters",
    response_model=ShelterListResponse,
    status_code=status.HTTP_200_OK,
    summary="List configured shelters",
    description="Return the complete configured shelter dataset.",
    operation_id="getShelters",
    responses={
        status.HTTP_200_OK: {"description": "Configured shelter records returned."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "The application could not complete the request.",
        },
    },
)
def get_shelters(
    use_case: ViewSheltersUseCaseProtocol = Depends(get_shelter_use_case),
) -> ShelterListResponse:
    """Return configured shelter records translated from the use-case DTO."""
    return ShelterListResponse.from_dto(use_case.execute())
