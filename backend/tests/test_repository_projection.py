"""Repository-boundary projection tests for the production CSV datasets."""

from datetime import datetime, timezone
from pathlib import Path
import unittest

from backend.app.data.file_support import DatasetFileFormat
from backend.app.data.models import (
    DatasetColumn,
    DatasetColumnType,
    DatasetMetadata,
    DatasetSchema,
)
from backend.app.data.repositories import CSVRepository
from backend.app.data.repository_config import FileRepositoryConfig
from backend.app.services.services import ShelterService, VillageService


DATASETS_DIRECTORY = Path(__file__).parents[2] / "data" / "datasets"


def _metadata(name: str) -> DatasetMetadata:
    """Build explicit metadata used only to configure the repository test."""
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return DatasetMetadata(
        name=name,
        description="Production CSV projection test dataset.",
        version="1.0.0",
        source="production dataset fixture",
        created_at=timestamp,
        updated_at=timestamp,
    )


def _schema(*columns: tuple[str, DatasetColumnType]) -> DatasetSchema:
    """Build the frozen application-facing table schema for one repository."""
    return DatasetSchema(
        columns=tuple(
            DatasetColumn(
                name=name,
                data_type=data_type,
                nullable=name in {"population", "capacity"},
            )
            for name, data_type in columns
        )
    )


class ProductionRepositoryProjectionTests(unittest.TestCase):
    """Verify real production rows are projected before frozen DTO construction."""

    def test_village_production_rows_project_to_application_columns(self) -> None:
        """Village production rows expose only name, district, and population."""
        repository = CSVRepository(
            FileRepositoryConfig(
                dataset_path=str(DATASETS_DIRECTORY / "villages.csv"),
                dataset_metadata=_metadata("Production villages"),
                dataset_schema=_schema(
                    ("name", DatasetColumnType.STRING),
                    ("district", DatasetColumnType.STRING),
                    ("population", DatasetColumnType.INTEGER),
                ),
                file_format=DatasetFileFormat.CSV,
            )
        )

        table = repository.load()
        villages = VillageService(repository).load_villages()

        self.assertEqual(
            tuple(column.name for column in table.dataset_schema.columns),
            ("name", "district", "population"),
        )
        self.assertEqual(len(table.rows), len(villages.villages))
        self.assertTrue(villages.villages[0].name)

    def test_shelter_production_rows_project_to_application_columns(self) -> None:
        """Shelter production rows expose only name, district, and capacity."""
        repository = CSVRepository(
            FileRepositoryConfig(
                dataset_path=str(DATASETS_DIRECTORY / "shelters.csv"),
                dataset_metadata=_metadata("Production shelters"),
                dataset_schema=_schema(
                    ("name", DatasetColumnType.STRING),
                    ("district", DatasetColumnType.STRING),
                    ("capacity", DatasetColumnType.INTEGER),
                ),
                file_format=DatasetFileFormat.CSV,
            )
        )

        table = repository.load()
        shelters = ShelterService(repository).load_shelters()

        self.assertEqual(
            tuple(column.name for column in table.dataset_schema.columns),
            ("name", "district", "capacity"),
        )
        self.assertEqual(len(table.rows), len(shelters.shelters))
        self.assertTrue(shelters.shelters[0].name)
