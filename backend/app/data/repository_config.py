"""Immutable configuration contracts for future file-backed repositories."""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from backend.app.data.exceptions import DatasetValidationError
from backend.app.data.file_support import (DatasetFileFormat,
                                           detect_supported_file)
from backend.app.data.models import DatasetMetadata, DatasetSchema
from backend.app.data.validation import validate_dataset_path


class FileRepositoryConfig(BaseModel):
    """Describe explicit dependencies required by a future file-backed repository.

    The caller supplies dataset metadata and schema; this contract performs only
    structural consistency checks and never accesses the configured filesystem path.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset_path: str
    dataset_metadata: DatasetMetadata
    dataset_schema: DatasetSchema
    file_format: DatasetFileFormat

    @field_validator("dataset_path", mode="before")
    @classmethod
    def validate_configured_path(cls, value: object) -> str:
        """Validate a nonblank dataset path without accessing the filesystem."""

        return validate_dataset_path(value)

    @field_validator("dataset_metadata", mode="before")
    @classmethod
    def validate_configured_metadata(cls, value: object) -> DatasetMetadata:
        """Require an explicit validated dataset metadata model."""

        if not isinstance(value, DatasetMetadata):
            raise DatasetValidationError(
                "Repository configuration requires a DatasetMetadata model."
            )
        return value

    @field_validator("dataset_schema", mode="before")
    @classmethod
    def validate_configured_schema(cls, value: object) -> DatasetSchema:
        """Require an explicit validated dataset schema model."""

        if not isinstance(value, DatasetSchema):
            raise DatasetValidationError(
                "Repository configuration requires a DatasetSchema model."
            )
        return value

    @field_validator("file_format", mode="before")
    @classmethod
    def validate_configured_format(cls, value: object) -> DatasetFileFormat:
        """Require an explicit supported file format value."""

        if not isinstance(value, DatasetFileFormat):
            raise DatasetValidationError(
                "Repository configuration requires a DatasetFileFormat value."
            )
        return value

    @model_validator(mode="after")
    def validate_format_matches_path(self) -> "FileRepositoryConfig":
        """Ensure the declared format matches the configured path extension."""

        if detect_supported_file(self.dataset_path) is not self.file_format:
            raise DatasetValidationError(
                "Repository configuration file format must match the dataset path extension."
            )
        return self
