"""Data-layer exception hierarchy for dataset contract validation."""


class DataException(Exception):
    """Base exception for data-layer contract failures."""


class DatasetValidationError(DataException):
    """Raised when a dataset contract value fails validation."""


class DatasetMetadataError(DataException):
    """Raised when dataset metadata is internally inconsistent."""


class DatasetRepositoryError(DataException):
    """Raised when a future dataset repository operation fails."""


class DatasetFormatError(DataException):
    """Raised when a future dataset format cannot be processed."""
