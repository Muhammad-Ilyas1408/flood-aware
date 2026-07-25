"""Small CDS API adapter for downloading opaque GloFAS forecast snapshots."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

import cdsapi

from backend.app.forecast.exceptions import (
    ForecastAuthenticationError,
    ForecastClientError,
    ForecastConfigurationError,
    ForecastDownloadError,
    ForecastPermissionError,
    ForecastTimeoutError,
    ForecastUnexpectedResponseError,
)
from backend.app.forecast.settings import ForecastSettings


class _CDSClientProtocol(Protocol):
    """Describe the minimal CDS API capability used by ``GloFASClient``."""

    def retrieve(
        self,
        name: str,
        request: Mapping[str, object],
        target: str,
    ) -> object:
        """Retrieve a requested dataset to the supplied target path."""


class GloFASClient:
    """Download GloFAS data while isolating CDS API concerns from ingestion."""

    def __init__(
        self,
        settings: ForecastSettings,
        client: _CDSClientProtocol | None = None,
    ) -> None:
        """Initialize a CDS API client from validated settings or an injected client.

        Args:
            settings: Immutable GloFAS connection and request configuration.
            client: Optional CDS-compatible client for tests or alternate adapters.

        Raises:
            ForecastConfigurationError: If no EWDS personal access token is configured.
            ForecastClientError: If CDS client construction fails.
        """

        if not settings.glofas_api_key:
            raise ForecastConfigurationError("GLOFAS_API_KEY is required.")

        self._owns_client = client is None
        self._settings = settings
        try:
            self._client = client or cdsapi.Client(
                url=settings.glofas_base_url,
                key=settings.glofas_api_key,
                timeout=settings.glofas_request_timeout,
                quiet=True,
                progress=False,
            )
        except Exception as error:
            raise _translate_cds_error(error) from error

    def close(self) -> None:
        """Close the internally owned CDS HTTP session when it is available."""

        if not self._owns_client:
            return
        session = getattr(self._client, "session", None)
        close = getattr(session, "close", None)
        if callable(close):
            close()

    def download_snapshot(
        self,
        request: Mapping[str, object],
        target_path: Path,
    ) -> Path:
        """Download one requested GloFAS snapshot and validate the saved file.

        Args:
            request: Validated CDS request parameters created by the ingestion service.
            target_path: New local path where the opaque NetCDF snapshot is saved.

        Returns:
            The saved snapshot path.

        Raises:
            ForecastDownloadError: If the target already exists or download fails.
            ForecastUnexpectedResponseError: If CDS does not create a non-empty file.
        """

        if target_path.exists():
            raise ForecastDownloadError(
                f"Refusing to overwrite existing GloFAS snapshot: {target_path}"
            )

        try:
            self._client.retrieve(
                self._settings.dataset_name,
                dict(request),
                str(target_path),
            )
        except Exception as error:
            raise _translate_cds_error(error) from error

        if not target_path.is_file() or target_path.stat().st_size == 0:
            raise ForecastUnexpectedResponseError(
                "GloFAS completed without producing a non-empty snapshot file."
            )
        return target_path


def _translate_cds_error(error: Exception) -> ForecastClientError:
    """Translate CDS API failures without leaking provider exception types.

    Args:
        error: Exception raised by CDS API client construction or retrieval.

    Returns:
        A precise Forecast ingestion exception.
    """

    message = str(error).lower()
    exception_name = type(error).__name__.lower()
    if "timeout" in message or "timeout" in exception_name:
        return ForecastTimeoutError("GloFAS request timed out.")
    if any(
        token in message for token in ("401", "unauthor", "authentication", "api key")
    ):
        return ForecastAuthenticationError(
            "EWDS rejected the configured GloFAS API key."
        )
    if any(token in message for token in ("403", "forbidden", "permission", "terms")):
        return ForecastPermissionError(
            "EWDS access was denied. Accept the CEMS-FLOODS dataset terms and verify access."
        )
    return ForecastDownloadError("GloFAS snapshot download failed.")
