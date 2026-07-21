"""Pure validation utilities for shared dataset metadata contracts."""

from backend.app.data.exceptions import DatasetValidationError
from backend.app.gis.geometry import BoundingBox


def validate_dataset_name(name: object) -> str:
    """Validate and return a nonblank dataset name.

    Raises:
        DatasetValidationError: If the name is not a nonblank string.
    """

    return _validate_nonblank_text(name, "Dataset name")


def validate_dataset_version(version: object) -> str:
    """Validate and return a nonblank dataset version.

    Raises:
        DatasetValidationError: If the version is not a nonblank string.
    """

    return _validate_nonblank_text(version, "Dataset version")


def validate_dataset_source(source: object) -> str:
    """Validate and return a nonblank dataset source description.

    Raises:
        DatasetValidationError: If the source is not a nonblank string.
    """

    if not isinstance(source, str) or not source.strip():
        raise DatasetValidationError("Dataset source must be a nonblank string.")
    return source


def validate_dataset_path(path: object) -> str:
    """Validate and return a nonblank dataset path without accessing the filesystem.

    Raises:
        DatasetValidationError: If the path is not a nonblank string.
    """

    return _validate_nonblank_text(path, "Dataset path")


def validate_dataset_description(description: object) -> str:
    """Validate and return a dataset description.

    Empty descriptions are valid, but descriptions must always be strings.

    Raises:
        DatasetValidationError: If the description is not a string.
    """

    if not isinstance(description, str):
        raise DatasetValidationError("Dataset description must be a string.")
    return description


def validate_dataset_bounds(bounds: object) -> BoundingBox:
    """Validate and return spatial bounds represented by a GIS bounding box.

    Raises:
        DatasetValidationError: If the bounds are not a ``BoundingBox``.
    """

    if not isinstance(bounds, BoundingBox):
        raise DatasetValidationError("Dataset bounds must be a BoundingBox.")
    return bounds


def _validate_nonblank_text(value: object, field_name: str) -> str:
    """Validate a required textual dataset metadata value."""

    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(f"{field_name} must be a nonblank string.")
    return value
