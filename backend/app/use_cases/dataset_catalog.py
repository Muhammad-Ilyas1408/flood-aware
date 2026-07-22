"""Application use case for viewing the configured dataset catalog."""

from backend.app.dtos.datasets import DatasetCatalogDTO
from backend.app.services.protocols import DatasetCatalogServiceProtocol


class ViewDatasetCatalogUseCase:
    """Coordinate the application task of viewing the dataset catalog."""

    def __init__(self, service: DatasetCatalogServiceProtocol) -> None:
        """Initialize the use case with its dataset catalog service dependency."""

        self._service: DatasetCatalogServiceProtocol = service

    def execute(self) -> DatasetCatalogDTO:
        """Return configured dataset summaries without transforming the DTO."""

        return self._service.load_catalog()
