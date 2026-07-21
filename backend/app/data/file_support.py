"""Shared read-only filesystem support for CSV and GeoJSON datasets."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Final

from backend.app.data.exceptions import DatasetFormatError, DatasetRepositoryError
from backend.app.data.validation import validate_dataset_path


class DatasetFileFormat(StrEnum):
    """Represent dataset file formats supported by the current infrastructure."""

    CSV = "csv"
    GEOJSON = "geojson"


@dataclass(frozen=True, slots=True)
class FileMetadata:
    """Describe filesystem metadata that can be determined without interpreting data."""

    path: Path
    filename: str
    extension: str
    size_bytes: int
    created_at: datetime | None
    modified_at: datetime
    file_format: DatasetFileFormat


_SUPPORTED_EXTENSIONS: Final[dict[str, DatasetFileFormat]] = {
    ".csv": DatasetFileFormat.CSV,
    ".geojson": DatasetFileFormat.GEOJSON,
}


def detect_supported_file(path: str | Path) -> DatasetFileFormat:
    """Return the supported dataset format for a path extension.

    Raises:
        DatasetFormatError: If the path does not use a supported dataset extension.
    """

    extension = Path(path).suffix.lower()
    try:
        return _SUPPORTED_EXTENSIONS[extension]
    except KeyError as error:
        raise DatasetFormatError(
            f"Unsupported dataset file extension: {extension or '(none)'}."
        ) from error


def validate_file_readiness(path: str | Path) -> Path:
    """Validate and return a readable dataset file path.

    Raises:
        DatasetRepositoryError: If the dataset file does not exist, is not a file,
            or is unreadable.
    """

    dataset_path = Path(validate_dataset_path(str(path)))
    if not dataset_path.exists():
        raise DatasetRepositoryError("Dataset file does not exist.")
    if not dataset_path.is_file():
        raise DatasetRepositoryError("Dataset path must reference a file.")

    try:
        with dataset_path.open("rb"):
            return dataset_path
    except OSError as error:
        raise DatasetRepositoryError("Dataset file is not readable.") from error


def extract_file_metadata(path: str | Path) -> FileMetadata:
    """Extract filesystem metadata that exists for a supported readable dataset file.

    Raises:
        DatasetFormatError: If the file extension is unsupported.
        DatasetRepositoryError: If the file is not ready for reading or cannot be inspected.
    """

    dataset_path = validate_file_readiness(path)
    file_format = detect_supported_file(dataset_path)
    try:
        file_status = dataset_path.stat()
    except OSError as error:
        raise DatasetRepositoryError("Dataset file metadata cannot be read.") from error

    creation_timestamp = getattr(file_status, "st_birthtime", None)
    created_at = (
        datetime.fromtimestamp(creation_timestamp, timezone.utc)
        if creation_timestamp is not None
        else None
    )
    return FileMetadata(
        path=dataset_path,
        filename=dataset_path.name,
        extension=dataset_path.suffix.lower(),
        size_bytes=file_status.st_size,
        created_at=created_at,
        modified_at=datetime.fromtimestamp(file_status.st_mtime, timezone.utc),
        file_format=file_format,
    )


def read_dataset_text(path: str | Path) -> str:
    """Read and return UTF-8 text from a validated dataset file.

    Raises:
        DatasetRepositoryError: If the dataset file cannot be read as UTF-8 text.
    """

    dataset_path = validate_file_readiness(path)
    try:
        return dataset_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise DatasetRepositoryError("Dataset file cannot be read as UTF-8 text.") from error
