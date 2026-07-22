"""Immutable runtime configuration contracts for application datasets."""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from backend.app.data.exceptions import DatasetValidationError
from backend.app.data.file_support import DatasetFileFormat
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
