"""Read-only GeoJSON validation and feature-counting infrastructure."""

from pathlib import Path

from backend.app.data.exceptions import DatasetFormatError
from backend.app.data.file_support import (DatasetFileFormat,
                                           detect_supported_file,
                                           read_dataset_text)
from backend.app.gis.exceptions import GeoJSONError
from backend.app.gis.geojson import (FeatureCollection,
                                     feature_collection_from_json)


def validate_geojson_file(path: str | Path) -> None:
    """Validate that a readable GeoJSON file is a supported FeatureCollection.

    Raises:
        DatasetFormatError: If the file is not GeoJSON or has invalid GeoJSON structure.
        DatasetRepositoryError: If the file cannot be read.
    """

    _validate_geojson_structure(path)


def count_geojson_features(path: str | Path) -> int:
    """Return the feature count from a validated GeoJSON FeatureCollection.

    Raises:
        DatasetFormatError: If the file is not GeoJSON or has invalid GeoJSON structure.
        DatasetRepositoryError: If the file cannot be read.
    """

    return len(_validate_geojson_structure(path).features)


def load_geojson_feature_collection(path: str | Path) -> FeatureCollection:
    """Load a validated Point-only GeoJSON FeatureCollection from a dataset file.

    Raises:
        DatasetFormatError: If the file is not GeoJSON or has invalid GeoJSON structure.
        DatasetRepositoryError: If the file cannot be read.
    """

    return _validate_geojson_structure(path)


def _validate_geojson_structure(path: str | Path) -> FeatureCollection:
    """Validate GeoJSON structure and return the parsed FeatureCollection."""

    if detect_supported_file(path) is not DatasetFileFormat.GEOJSON:
        raise DatasetFormatError("Dataset file must use the .geojson extension.")

    try:
        return feature_collection_from_json(read_dataset_text(path))
    except GeoJSONError as error:
        raise DatasetFormatError("GeoJSON dataset must be a valid FeatureCollection.") from error
