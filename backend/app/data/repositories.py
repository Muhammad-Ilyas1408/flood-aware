"""Concrete read-only repositories for configured dataset files."""

import csv
from io import StringIO

from backend.app.data.csv_support import validate_csv_file
from backend.app.data.exceptions import (DatasetFormatError,
                                         DatasetValidationError)
from backend.app.data.file_support import DatasetFileFormat, read_dataset_text
from backend.app.data.geojson_support import (load_geojson_feature_collection,
                                              validate_geojson_file)
from backend.app.data.models import (DatasetMetadata, DatasetSchema,
                                     DatasetTable)
from backend.app.data.repository_config import FileRepositoryConfig
from backend.app.data.serialization import (
    csv_to_dataset_table, feature_collection_to_dataset_table,
    row_mappings_to_dataset_table)


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
        csv_text = read_dataset_text(self._config.dataset_path)
        projected_rows = _project_production_rows(
            csv_text,
            self._config.dataset_schema,
        )
        if projected_rows is not None:
            return row_mappings_to_dataset_table(
                projected_rows,
                self._config.dataset_schema,
            )
        return csv_to_dataset_table(
            csv_text,
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


def _project_production_rows(
    csv_text: str,
    schema: DatasetSchema,
) -> tuple[dict[str, str], ...] | None:
    """Project known production rows into the frozen application row shape.

    Village and shelter production files retain their full external columns on
    disk. This repository-boundary step creates new row mappings with only the
    fields required by the configured application schema.
    """

    expected_headers = tuple(column.name for column in schema.columns)
    try:
        reader = csv.DictReader(StringIO(csv_text), strict=True)
        source_headers = reader.fieldnames
        if source_headers is None:
            return None

        projection = _production_projection(source_headers, expected_headers)
        if projection is None:
            return None

        projected_rows: list[dict[str, str]] = []
        for source_row in reader:
            if None in source_row or any(value is None for value in source_row.values()):
                raise DatasetValidationError(
                    "CSV row value count must match the supplied schema."
                )
            projected_row = {
                destination: source_row[source]
                for destination, source in zip(expected_headers, projection, strict=True)
            }
            if expected_headers == ("name", "district", "population"):
                projected_row["population"] = _normalize_nullable_value(
                    projected_row["population"]
                )
            projected_rows.append(projected_row)
        return tuple(projected_rows)
    except csv.Error as error:
        raise DatasetFormatError("CSV input is malformed.") from error


def _production_projection(
    source_headers: list[str],
    expected_headers: tuple[str, ...],
) -> tuple[str, ...] | None:
    """Return one supported explicit production projection, if applicable."""

    village_headers = ("name", "district", "population")
    shelter_headers = ("name", "district", "capacity")
    if expected_headers == village_headers and "village_name" in source_headers:
        return ("village_name", "district", "population")
    if expected_headers == shelter_headers and "shelter_name" in source_headers:
        return ("shelter_name", "district", "capacity")
    return None


def _normalize_nullable_value(value: str) -> str:
    """Convert the production CSV null token to the canonical CSV null form."""

    return "" if value == "NULL" else value
