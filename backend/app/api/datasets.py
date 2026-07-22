"""Dataset catalog API endpoint."""

from fastapi import APIRouter, Depends, status

from backend.app.composition import get_dataset_catalog_service
from backend.app.schemas.datasets import DatasetCatalogResponse
from backend.app.schemas.errors import ErrorResponse
from backend.app.services.protocols import DatasetCatalogServiceProtocol


router = APIRouter(tags=["Datasets"])


@router.get(
    "/datasets/catalog",
    response_model=DatasetCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get configured dataset catalog",
    description="Return independent summaries for configured village and shelter datasets.",
    operation_id="getDatasetCatalog",
    responses={
        status.HTTP_200_OK: {"description": "Configured dataset catalog returned."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "The application could not complete the request.",
        },
    },
)
def get_dataset_catalog(
    service: DatasetCatalogServiceProtocol = Depends(get_dataset_catalog_service),
) -> DatasetCatalogResponse:
    """Return configured dataset summaries translated from the service DTO."""
    return DatasetCatalogResponse.from_dto(service.load_catalog())
