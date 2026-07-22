"""Service implementations that coordinate access to dataset repositories."""

from backend.app.data.models import DatasetTable
from backend.app.data.protocols import DatasetTableRepositoryProtocol
from backend.app.data.repositories import CSVRepository


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


class VillageService:
    """Load the configured village dataset through a CSV repository."""

    def __init__(self, repository: CSVRepository) -> None:
        """Initialize the service with the configured village CSV repository.

        Args:
            repository: The CSV repository that supplies the village dataset.
        """
        self._dataset_service: DatasetService = DatasetService(repository)

    def load_villages(self) -> DatasetTable:
        """Load and return the complete village dataset table."""
        return self._dataset_service.load_dataset()


class ShelterService:
    """Load the configured shelter dataset through a CSV repository."""

    def __init__(self, repository: CSVRepository) -> None:
        """Initialize the service with the configured shelter CSV repository.

        Args:
            repository: The CSV repository that supplies the shelter dataset.
        """
        self._dataset_service: DatasetService = DatasetService(repository)

    def load_shelters(self) -> DatasetTable:
        """Load and return the complete shelter dataset table."""
        return self._dataset_service.load_dataset()
