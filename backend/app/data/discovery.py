"""Deterministic, non-recursive discovery of supported dataset files."""

from pathlib import Path

from backend.app.data.exceptions import DatasetRepositoryError
from backend.app.data.file_support import FileMetadata, extract_file_metadata
from backend.app.data.validation import validate_dataset_path


def discover_datasets(directory: str | Path) -> tuple[FileMetadata, ...]:
    """Discover supported dataset files in a directory in deterministic filename order.

    Every regular file encountered must use a supported extension; unsupported files
    are rejected rather than silently ignored. Subdirectories are not traversed.

    Raises:
        DatasetRepositoryError: If the directory is unavailable or cannot be inspected.
        DatasetFormatError: If a regular file uses an unsupported extension.
    """

    directory_path = Path(validate_dataset_path(str(directory)))
    if not directory_path.exists():
        raise DatasetRepositoryError("Dataset directory does not exist.")
    if not directory_path.is_dir():
        raise DatasetRepositoryError("Dataset discovery path must reference a directory.")

    try:
        dataset_paths = sorted(
            (path for path in directory_path.iterdir() if path.is_file()),
            key=lambda path: path.name.casefold(),
        )
    except OSError as error:
        raise DatasetRepositoryError("Dataset directory cannot be inspected.") from error

    return tuple(extract_file_metadata(path) for path in dataset_paths)
