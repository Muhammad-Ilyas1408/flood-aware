"""Unit tests for application use cases and their service coordination."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

from backend.app.data.models import DatasetMetadata, DatasetStatistics
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageDTO,
    VillageListDTO,
)
from backend.app.services.protocols import (
    DatasetCatalogServiceProtocol,
    ShelterServiceProtocol,
    VillageServiceProtocol,
)
from backend.app.use_cases.dataset_catalog import ViewDatasetCatalogUseCase
from backend.app.use_cases.shelters import ViewSheltersUseCase
from backend.app.use_cases.villages import ViewVillagesUseCase


def _dataset_metadata(name: str) -> DatasetMetadata:
    """Create immutable metadata required by a dataset summary DTO."""

    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    return DatasetMetadata(
        name=name,
        description="Use-case unit test dataset.",
        version="1.0.0",
        source="unit test",
        created_at=timestamp,
        updated_at=timestamp,
    )


def _dataset_catalog_dto() -> DatasetCatalogDTO:
    """Create an immutable catalog DTO for use-case passthrough tests."""

    return DatasetCatalogDTO(
        villages=DatasetSummaryDTO(
            metadata=_dataset_metadata("Villages"),
            statistics=DatasetStatistics(record_count=1),
        ),
        shelters=DatasetSummaryDTO(
            metadata=_dataset_metadata("Shelters"),
            statistics=DatasetStatistics(record_count=1),
        ),
    )


def test_view_villages_use_case_delegates_to_service() -> None:
    """Village use case invokes the injected village service exactly once."""

    service = create_autospec(VillageServiceProtocol, instance=True, spec_set=True)
    service.load_villages.return_value = VillageListDTO(villages=())

    ViewVillagesUseCase(service).execute()

    service.load_villages.assert_called_once_with()


def test_view_villages_use_case_returns_service_dto() -> None:
    """Village use case returns the exact DTO produced by its service."""

    expected_dto = VillageListDTO(
        villages=(
            VillageDTO(
                name="Kalam",
                district="Swat",
                population=5000,
                latitude=35.5000,
                longitude=72.6000,
            ),
        )
    )
    service = create_autospec(VillageServiceProtocol, instance=True, spec_set=True)
    service.load_villages.return_value = expected_dto

    returned_dto = ViewVillagesUseCase(service).execute()

    assert returned_dto is expected_dto
    service.load_villages.assert_called_once_with()


def test_view_shelters_use_case_delegates_to_service() -> None:
    """Shelter use case invokes the injected shelter service exactly once."""

    service = create_autospec(ShelterServiceProtocol, instance=True, spec_set=True)
    service.load_shelters.return_value = ShelterListDTO(shelters=())

    ViewSheltersUseCase(service).execute()

    service.load_shelters.assert_called_once_with()


def test_view_shelters_use_case_returns_service_dto() -> None:
    """Shelter use case returns the exact DTO produced by its service."""

    expected_dto = ShelterListDTO(
        shelters=(
            ShelterDTO(
                name="Government High School Akora",
                district="Nowshera",
                capacity=500,
                latitude=33.8245,
                longitude=72.1282,
            ),
        )
    )
    service = create_autospec(ShelterServiceProtocol, instance=True, spec_set=True)
    service.load_shelters.return_value = expected_dto

    returned_dto = ViewSheltersUseCase(service).execute()

    assert returned_dto is expected_dto
    service.load_shelters.assert_called_once_with()


def test_view_dataset_catalog_use_case_delegates_to_service() -> None:
    """Catalog use case invokes the injected catalog service exactly once."""

    service = create_autospec(
        DatasetCatalogServiceProtocol,
        instance=True,
        spec_set=True,
    )
    service.load_catalog.return_value = _dataset_catalog_dto()

    ViewDatasetCatalogUseCase(service).execute()

    service.load_catalog.assert_called_once_with()


def test_view_dataset_catalog_use_case_returns_service_dto() -> None:
    """Catalog use case returns the exact DTO produced by its service."""

    expected_dto = _dataset_catalog_dto()
    service = create_autospec(
        DatasetCatalogServiceProtocol,
        instance=True,
        spec_set=True,
    )
    service.load_catalog.return_value = expected_dto

    returned_dto = ViewDatasetCatalogUseCase(service).execute()

    assert returned_dto is expected_dto
    service.load_catalog.assert_called_once_with()
