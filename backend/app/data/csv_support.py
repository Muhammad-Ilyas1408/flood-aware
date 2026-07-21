"""Read-only CSV validation and record-counting infrastructure."""

import csv
from io import StringIO
from pathlib import Path

from backend.app.data.exceptions import DatasetFormatError
from backend.app.data.file_support import (
    DatasetFileFormat,
    detect_supported_file,
    read_dataset_text,
)


def validate_csv_file(path: str | Path) -> None:
    """Validate that a readable CSV file has a header and parseable records.

    Raises:
        DatasetFormatError: If the file is not CSV or has invalid CSV structure.
        DatasetRepositoryError: If the file cannot be read.
    """

    _validate_csv_structure(path)


def count_csv_records(path: str | Path) -> int:
    """Return the number of data records in a validated CSV file.

    Raises:
        DatasetFormatError: If the file is not CSV or has invalid CSV structure.
        DatasetRepositoryError: If the file cannot be read.
    """

    return len(_validate_csv_structure(path))


def _validate_csv_structure(
    path: str | Path,
) -> tuple[dict[str | None, str | list[str] | None], ...]:
    """Validate CSV structure and return its parsed records for internal use."""

    if detect_supported_file(path) is not DatasetFileFormat.CSV:
        raise DatasetFormatError("Dataset file must use the .csv extension.")

    try:
        reader = csv.DictReader(StringIO(read_dataset_text(path)))
        if reader.fieldnames is None:
            raise DatasetFormatError("CSV dataset must include a header row.")
        return tuple(reader)
    except csv.Error as error:
        raise DatasetFormatError("CSV dataset structure is invalid.") from error
