"""Explicit dependency construction for Flood-Aware dataset services."""

from backend.app.data.file_support import DatasetFileFormat
from backend.app.data.models import DatasetMetadata, DatasetSchema
from backend.app.data.protocols import DatasetTableRepositoryProtocol
from backend.app.data.repositories import CSVRepository
from backend.app.data.repository_config import FileRepositoryConfig
from backend.app.services.services import DatasetService, ShelterService, VillageService


def create_dataset_service(
    repository: DatasetTableRepositoryProtocol,
) -> DatasetService:
    """Create a service that loads complete dataset tables from a repository.

    Args:
        repository: The explicit repository used by the service.

    Returns:
        A ready-to-use dataset service.
    """
    return DatasetService(repository)


def create_village_service(
    dataset_path: str,
    dataset_metadata: DatasetMetadata,
    dataset_schema: DatasetSchema,
) -> VillageService:
    """Create a village service backed by an explicitly configured CSV repository.

    Args:
        dataset_path: Path to the village CSV dataset.
        dataset_metadata: Explicit metadata for the village dataset.
        dataset_schema: Explicit schema for the village dataset.

    Returns:
        A ready-to-use village service.

    Raises:
        DatasetValidationError: If the supplied repository configuration is invalid.
    """
    return VillageService(
        _create_csv_repository(dataset_path, dataset_metadata, dataset_schema)
    )


def create_shelter_service(
    dataset_path: str,
    dataset_metadata: DatasetMetadata,
    dataset_schema: DatasetSchema,
) -> ShelterService:
    """Create a shelter service backed by an explicitly configured CSV repository.

    Args:
        dataset_path: Path to the shelter CSV dataset.
        dataset_metadata: Explicit metadata for the shelter dataset.
        dataset_schema: Explicit schema for the shelter dataset.

    Returns:
        A ready-to-use shelter service.

    Raises:
        DatasetValidationError: If the supplied repository configuration is invalid.
    """
    return ShelterService(
        _create_csv_repository(dataset_path, dataset_metadata, dataset_schema)
    )


def _create_csv_repository(
    dataset_path: str,
    dataset_metadata: DatasetMetadata,
    dataset_schema: DatasetSchema,
) -> CSVRepository:
    """Construct a CSV repository from explicit validated dependencies."""
    return CSVRepository(
        FileRepositoryConfig(
            dataset_path=dataset_path,
            dataset_metadata=dataset_metadata,
            dataset_schema=dataset_schema,
            file_format=DatasetFileFormat.CSV,
        )
    )
