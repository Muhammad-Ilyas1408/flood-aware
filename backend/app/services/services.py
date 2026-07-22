"""Service implementations that prepare application dataset DTOs."""

from backend.app.data.models import DatasetStatistics, DatasetTable
from backend.app.data.protocols import DatasetTableRepositoryProtocol
from backend.app.data.repositories import CSVRepository
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageDTO,
    VillageListDTO,
)
from backend.app.services.protocols import ShelterServiceProtocol, VillageServiceProtocol


class DatasetService:
    """Load complete dataset tables through an injected repository contract."""

    def __init__(self, repository: DatasetTableRepositoryProtocol) -> None:
        """Initialize the service with a repository that provides a dataset table.

        Args:
            repository: The repository used to load the complete dataset table.
        """
        self._repository: DatasetTableRepositoryProtocol = repository

    def load_dataset(self) -> DatasetTable:
        """Load and return the complete dataset table from the repository."""
        return self._repository.load()

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return application-ready metadata and exact record statistics."""
        table = self.load_dataset()
        return DatasetSummaryDTO(
            metadata=self._repository.metadata(),
            statistics=DatasetStatistics(record_count=len(table.rows)),
        )


class VillageService:
    """Load the configured village dataset through a CSV repository."""

    def __init__(self, repository: CSVRepository) -> None:
        """Initialize the service with the configured village CSV repository.

        Args:
            repository: The CSV repository that supplies the village dataset.
        """
        self._dataset_service: DatasetService = DatasetService(repository)

    def load_villages(self) -> VillageListDTO:
        """Load and return application-ready village records."""
        table = self._dataset_service.load_dataset()
        return VillageListDTO(
            villages=tuple(
                VillageDTO(**row)
                for row in _table_rows_as_mappings(table)
            )
        )

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return the configured village dataset summary."""
        return self._dataset_service.load_summary()


class ShelterService:
    """Load the configured shelter dataset through a CSV repository."""

    def __init__(self, repository: CSVRepository) -> None:
        """Initialize the service with the configured shelter CSV repository.

        Args:
            repository: The CSV repository that supplies the shelter dataset.
        """
        self._dataset_service: DatasetService = DatasetService(repository)

    def load_shelters(self) -> ShelterListDTO:
        """Load and return application-ready shelter records."""
        table = self._dataset_service.load_dataset()
        return ShelterListDTO(
            shelters=tuple(
                ShelterDTO(**row)
                for row in _table_rows_as_mappings(table)
            )
        )

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return the configured shelter dataset summary."""
        return self._dataset_service.load_summary()


class DatasetCatalogService:
    """Prepare independent summaries for the configured application datasets."""

    def __init__(
        self,
        village_service: VillageServiceProtocol,
        shelter_service: ShelterServiceProtocol,
    ) -> None:
        """Initialize the catalog service with configured dataset services.

        Args:
            village_service: The service that provides the village summary.
            shelter_service: The service that provides the shelter summary.
        """
        self._village_service: VillageServiceProtocol = village_service
        self._shelter_service: ShelterServiceProtocol = shelter_service

    def load_catalog(self) -> DatasetCatalogDTO:
        """Load independent summaries for villages and shelters without aggregation."""
        return DatasetCatalogDTO(
            villages=self._village_service.load_summary(),
            shelters=self._shelter_service.load_summary(),
        )


def _table_rows_as_mappings(table: DatasetTable) -> tuple[dict[str, object], ...]:
    """Return ordered row mappings keyed by the table's declared schema columns."""
    column_names = tuple(column.name for column in table.dataset_schema.columns)
    return tuple(
        dict(zip(column_names, row.values, strict=True)) for row in table.rows
    )
