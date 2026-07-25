"""Domain-specific failures for GloFAS forecast snapshot ingestion."""


class ForecastError(Exception):
    """Base exception for forecast ingestion failures."""


class ForecastConfigurationError(ForecastError):
    """Raised when required forecast ingestion configuration is unavailable."""


class ForecastClientError(ForecastError):
    """Raised when the GloFAS client cannot complete a provider operation."""


class ForecastAuthenticationError(ForecastClientError):
    """Raised when EWDS rejects the configured personal access token."""


class ForecastPermissionError(ForecastClientError):
    """Raised when the EWDS dataset licence or access permission is missing."""


class ForecastDownloadError(ForecastClientError):
    """Raised when a forecast snapshot cannot be downloaded or saved safely."""


class ForecastTimeoutError(ForecastDownloadError):
    """Raised when a GloFAS request exceeds its configured timeout."""


class ForecastUnexpectedResponseError(ForecastDownloadError):
    """Raised when a completed request does not produce a valid snapshot file."""


class ForecastSnapshotNotFoundError(ForecastError):
    """Raised when no locally stored forecast snapshot is available."""


class ForecastParsingError(ForecastError):
    """Raised when a local NetCDF forecast snapshot has an unsupported structure."""


class ForecastMappingError(ForecastError):
    """Raised when parsed forecast data cannot be mapped to domain objects."""
