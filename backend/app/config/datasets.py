"""Immutable runtime configuration contracts for application datasets."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from backend.app.data.exceptions import DatasetValidationError
from backend.app.config.settings import PROJECT_ROOT
from backend.app.data.file_support import DatasetFileFormat, extract_file_metadata
from backend.app.data.models import (
    DatasetColumn,
    DatasetColumnType,
    DatasetMetadata,
    DatasetSchema,
)
from backend.app.data.repository_config import FileRepositoryConfig


class DatasetCatalogConfig(BaseModel):
    """Provide explicit runtime repository configurations for application datasets.

    Callers supply fully validated repository configurations whose paths identify
    the deployment's dataset directory. This contract performs no filesystem
    access and does not infer metadata or schemas.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    villages: FileRepositoryConfig
    shelters: FileRepositoryConfig

    @field_validator("villages", "shelters", mode="before")
    @classmethod
    def validate_repository_config(cls, value: object) -> FileRepositoryConfig:
        """Require an explicit, validated file repository configuration."""

        if not isinstance(value, FileRepositoryConfig):
            raise DatasetValidationError(
                "Dataset catalog configuration requires a FileRepositoryConfig model."
            )
        return value

    @model_validator(mode="after")
    def validate_csv_repository_formats(self) -> "DatasetCatalogConfig":
        """Ensure current village and shelter services receive CSV configurations."""

        if self.villages.file_format is not DatasetFileFormat.CSV:
            raise DatasetValidationError(
                "Village dataset configuration must use the CSV file format."
            )
        if self.shelters.file_format is not DatasetFileFormat.CSV:
            raise DatasetValidationError(
                "Shelter dataset configuration must use the CSV file format."
            )
        return self


def create_production_dataset_catalog_config() -> DatasetCatalogConfig:
    """Create the explicit catalog configuration for checked-in production data.

    This bootstrap helper owns only production file paths, metadata, and the
    application-facing schemas required by the existing repository projection.
    It does not construct services or alter caller-supplied configuration.
    """
    datasets_directory = PROJECT_ROOT / "data" / "datasets"
    return DatasetCatalogConfig(
        villages=_production_csv_config(
            datasets_directory / "villages.csv",
            name="Flood-Aware production villages",
            description="Verified village records for Flood-Aware decision support.",
            columns=(
                ("name", DatasetColumnType.STRING, False),
                ("district", DatasetColumnType.STRING, False),
                ("population", DatasetColumnType.INTEGER, True),
                ("latitude", DatasetColumnType.FLOAT, False),
                ("longitude", DatasetColumnType.FLOAT, False),
            ),
            tags=("villages", "production"),
        ),
        shelters=_production_csv_config(
            datasets_directory / "shelters.csv",
            name="Flood-Aware production shelters",
            description="Verified shelter records for Flood-Aware decision support.",
            columns=(
                ("name", DatasetColumnType.STRING, False),
                ("district", DatasetColumnType.STRING, False),
                ("capacity", DatasetColumnType.INTEGER, True),
                ("latitude", DatasetColumnType.FLOAT, False),
                ("longitude", DatasetColumnType.FLOAT, False),
            ),
            tags=("shelters", "production"),
        ),
    )


def _production_csv_config(
    path: Path,
    *,
    name: str,
    description: str,
    columns: tuple[tuple[str, DatasetColumnType, bool], ...],
    tags: tuple[str, ...],
) -> FileRepositoryConfig:
    """Build one validated production CSV repository configuration."""
    file_metadata = extract_file_metadata(path)
    created_at = min(
        timestamp
        for timestamp in (file_metadata.created_at, file_metadata.modified_at)
        if timestamp is not None
    )
    return FileRepositoryConfig(
        dataset_path=str(file_metadata.path),
        dataset_metadata=DatasetMetadata(
            name=name,
            description=description,
            version="1.0.0",
            source=f"Flood-Aware checked-in dataset: {file_metadata.filename}",
            created_at=created_at,
            updated_at=file_metadata.modified_at,
            tags=tags,
        ),
        dataset_schema=DatasetSchema(
            columns=tuple(
                DatasetColumn(
                    name=column_name,
                    data_type=column_type,
                    nullable=nullable,
                )
                for column_name, column_type, nullable in columns
            )
        ),
        file_format=DatasetFileFormat.CSV,
    )
