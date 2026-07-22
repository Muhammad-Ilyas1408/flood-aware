"""Concrete read-only repositories for configured dataset files."""

from backend.app.data.csv_support import validate_csv_file
from backend.app.data.exceptions import DatasetFormatError, DatasetValidationError
from backend.app.data.file_support import DatasetFileFormat, read_dataset_text
from backend.app.data.geojson_support import (
    load_geojson_feature_collection,
    validate_geojson_file,
)
from backend.app.data.models import DatasetMetadata, DatasetTable
from backend.app.data.repository_config import FileRepositoryConfig
from backend.app.data.serialization import (
    csv_to_dataset_table,
    feature_collection_to_dataset_table,
)


class CSVRepository:
    """Read a configured CSV dataset as a :class:`DatasetTable`.

    Args:
        config: Immutable configuration that supplies the dataset path, metadata,
            schema, and expected file format.

    Raises:
        DatasetValidationError: If ``config`` is not a file repository
            configuration.
    """

    def __init__(self, config: FileRepositoryConfig) -> None:
        """Initialize the repository with its immutable configuration."""
        if not isinstance(config, FileRepositoryConfig):
            raise DatasetValidationError(
                "CSV repository requires a FileRepositoryConfig model."
            )
        self._config: FileRepositoryConfig = config

    def validate(self) -> None:
        """Validate the configured CSV file is ready for loading.

        Raises:
            DatasetFormatError: If the configuration does not specify CSV format
                or the configured file is not a valid CSV dataset.
            DatasetRepositoryError: If the configured file is not ready to read.
        """
        if self._config.file_format is not DatasetFileFormat.CSV:
            raise DatasetFormatError("CSV repository requires a CSV file configuration.")
        validate_csv_file(self._config.dataset_path)

    def metadata(self) -> DatasetMetadata:
        """Return the metadata explicitly supplied in the repository configuration."""
        return self._config.dataset_metadata

    def load(self) -> DatasetTable:
        """Load the configured CSV file into a validated dataset table.

        Returns:
            The CSV content deserialized according to the configured schema.

        Raises:
            DatasetFormatError: If the CSV content is malformed.
            DatasetRepositoryError: If the configured file cannot be read.
            DatasetValidationError: If CSV values do not satisfy the configured
                dataset schema.
        """
        self.validate()
        return csv_to_dataset_table(
            read_dataset_text(self._config.dataset_path),
            self._config.dataset_schema,
        )


class GeoJSONRepository:
    """Read a configured GeoJSON FeatureCollection as a :class:`DatasetTable`.

    Args:
        config: Immutable configuration that supplies the dataset path, metadata,
            schema, and expected file format.

    Raises:
        DatasetValidationError: If ``config`` is not a file repository
            configuration.
    """

    def __init__(self, config: FileRepositoryConfig) -> None:
        """Initialize the repository with its immutable configuration."""
        if not isinstance(config, FileRepositoryConfig):
            raise DatasetValidationError(
                "GeoJSON repository requires a FileRepositoryConfig model."
            )
        self._config: FileRepositoryConfig = config

    def validate(self) -> None:
        """Validate the configured GeoJSON FeatureCollection is ready to load.

        Raises:
            DatasetFormatError: If the configuration does not specify GeoJSON
                format or the configured file is not a valid FeatureCollection.
            DatasetRepositoryError: If the configured file is not ready to read.
        """
        if self._config.file_format is not DatasetFileFormat.GEOJSON:
            raise DatasetFormatError(
                "GeoJSON repository requires a GeoJSON file configuration."
            )
        validate_geojson_file(self._config.dataset_path)

    def metadata(self) -> DatasetMetadata:
        """Return the metadata explicitly supplied in the repository configuration."""
        return self._config.dataset_metadata

    def load(self) -> DatasetTable:
        """Load the configured GeoJSON file into a validated dataset table.

        Returns:
            Feature properties deserialized according to the configured schema.

        Raises:
            DatasetFormatError: If the GeoJSON content is malformed.
            DatasetRepositoryError: If the configured file cannot be read.
            DatasetValidationError: If feature properties do not satisfy the
                configured dataset schema.
        """
        self.validate()
        return feature_collection_to_dataset_table(
            load_geojson_feature_collection(self._config.dataset_path),
            self._config.dataset_schema,
        )
