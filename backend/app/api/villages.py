"""Village dataset API endpoint."""

from fastapi import APIRouter, Depends, Query, status

from backend.app.composition import get_village_use_case
from backend.app.config.graph_dependencies import get_village_summary_use_case
from backend.app.schemas.datasets import VillageListResponse
from backend.app.schemas.errors import ErrorResponse
from backend.app.schemas.village_summary import VillageSummaryListResponse
from backend.app.use_cases.protocols import (
    ViewVillageSummariesUseCaseProtocol,
    ViewVillagesUseCaseProtocol,
)

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


@router.get(
    "/villages/summary",
    response_model=VillageSummaryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Return lightweight condition summaries for requested villages",
    description=(
        "Return real current weather and a real, deterministic flood-severity "
        "classification for explicitly requested configured villages. Unlike "
        "/conversation, this never invokes GIS analysis, the LangGraph decision "
        "graph, or OpenAI, so it is meaningfully faster and free. Weather and "
        "severity are reported honestly: either may be unavailable without "
        "fabricating the other, and requested names not in the configured "
        "dataset are reported back rather than silently dropped."
    ),
    operation_id="getVillageSummaries",
    responses={
        status.HTTP_200_OK: {
            "description": "Village condition summaries returned."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "The request failed validation.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "The application could not complete the request.",
        },
    },
)
def get_village_summaries(
    names: list[str] = Query(
        ...,
        min_length=1,
        alias="names",
        description="One or more configured village names to summarize.",
    ),
    use_case: ViewVillageSummariesUseCaseProtocol = Depends(
        get_village_summary_use_case
    ),
) -> VillageSummaryListResponse:
    """Return condition summaries for requested villages translated from the DTO."""
    return VillageSummaryListResponse.from_dto(use_case.execute(tuple(names)))
