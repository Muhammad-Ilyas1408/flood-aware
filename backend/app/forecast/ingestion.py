"""Production-safe creation and storage of opaque GloFAS NetCDF snapshots."""

from datetime import UTC, date, datetime
from pathlib import Path

from netCDF4 import Dataset

from backend.app.forecast.client import GloFASClient
from backend.app.forecast.constants import (
    DEFAULT_DATA_FORMAT,
    DEFAULT_DOWNLOAD_FORMAT,
    DEFAULT_HYDROLOGICAL_MODEL,
    DEFAULT_PRODUCT_LABEL,
    DEFAULT_PRODUCT_TYPE,
    DEFAULT_SNAPSHOT_DIRECTORY,
    DEFAULT_SWAT_BOUNDING_BOX,
    DEFAULT_SYSTEM_VERSION,
    DEFAULT_VARIABLE,
)
from backend.app.forecast.exceptions import ForecastDownloadError
from backend.app.forecast.settings import ForecastSettings
from backend.app.gis.geometry import BoundingBox


_SNAPSHOT_METADATA_ATTRIBUTES = (
    "dataset_name",
    "product_type",
    "hydrological_model",
    "system_version",
)


class GloFASIngestionService:
    """Create, download, and persist a small unparsed GloFAS forecast snapshot."""

    def __init__(
        self,
        client: GloFASClient,
        settings: ForecastSettings,
        storage_directory: Path = DEFAULT_SNAPSHOT_DIRECTORY,
    ) -> None:
        """Initialize the ingestion service with injected provider infrastructure.

        Args:
            client: CDS-isolated GloFAS download adapter.
            settings: Immutable request configuration.
            storage_directory: Local directory used only for raw NetCDF snapshots.
        """

        self._client = client
        self._settings = settings
        self._storage_directory = storage_directory

    def ingest(
        self,
        forecast_date: date | None = None,
        bounds: BoundingBox = DEFAULT_SWAT_BOUNDING_BOX,
        ingested_at: datetime | None = None,
    ) -> Path:
        """Download one raw GloFAS snapshot for a bounded area.

        Args:
            forecast_date: UTC issue date; defaults to the current UTC date.
            bounds: WGS 84 area to submit as an EWDS bounding box.
            ingested_at: UTC ingestion timestamp used to create a deterministic filename.

        Returns:
            The newly saved NetCDF snapshot path.

        Raises:
            ForecastDownloadError: If the local snapshot path already exists.
        """

        request_date = forecast_date or datetime.now(UTC).date()
        timestamp = ingested_at or datetime.now(UTC)
        target_path = self._snapshot_path(timestamp)
        self._storage_directory.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            raise ForecastDownloadError(
                f"Refusing to overwrite existing GloFAS snapshot: {target_path}"
            )
        request = self._build_request(request_date, bounds)
        saved_path = self._client.download_snapshot(request, target_path)
        self._write_snapshot_metadata(saved_path, request)
        return saved_path

    def _build_request(self, forecast_date: date, bounds: BoundingBox) -> dict[str, object]:
        """Build the smallest supported control-forecast request for one lead time."""

        lead_time_hours = self._settings.glofas_default_forecast_days * 24
        return {
            "system_version": DEFAULT_SYSTEM_VERSION,
            "hydrological_model": DEFAULT_HYDROLOGICAL_MODEL,
            "product_type": DEFAULT_PRODUCT_TYPE,
            "variable": DEFAULT_VARIABLE,
            "year": f"{forecast_date:%Y}",
            "month": f"{forecast_date:%m}",
            "day": f"{forecast_date:%d}",
            "leadtime_hour": [str(lead_time_hours)],
            "area": [
                bounds.max_latitude,
                bounds.min_longitude,
                bounds.min_latitude,
                bounds.max_longitude,
            ],
            "data_format": DEFAULT_DATA_FORMAT,
            "download_format": DEFAULT_DOWNLOAD_FORMAT,
        }

    def _snapshot_path(self, ingested_at: datetime) -> Path:
        """Return the deterministic raw-snapshot path for an ingestion timestamp."""

        utc_timestamp = ingested_at.astimezone(UTC)
        filename = (
            f"glofas_{DEFAULT_PRODUCT_LABEL}_{utc_timestamp:%Y%m%dT%H%M%SZ}.nc"
        )
        return self._storage_directory / filename

    def _write_snapshot_metadata(
        self,
        snapshot_path: Path,
        request: dict[str, object],
    ) -> None:
        """Persist the exact request provenance required by local forecast parsing.

        The CDS NetCDF response supplies ECMWF/GRIB provenance but not the request
        attributes needed by the application-level forecast contract. These values
        are written only from the actual dataset setting and successful request.

        Args:
            snapshot_path: Newly downloaded NetCDF snapshot to annotate in place.
            request: Request payload submitted to the GloFAS dataset.

        Raises:
            ForecastDownloadError: If the downloaded NetCDF file cannot be annotated.
        """

        metadata = {
            "dataset_name": self._settings.dataset_name,
            "product_type": request["product_type"],
            "hydrological_model": request["hydrological_model"],
            "system_version": request["system_version"],
        }
        try:
            with Dataset(snapshot_path, mode="a") as dataset:
                for name in _SNAPSHOT_METADATA_ATTRIBUTES:
                    value = metadata[name]
                    if not isinstance(value, str) or not value.strip():
                        raise ForecastDownloadError(
                            f"Cannot persist required GloFAS metadata attribute: {name}"
                        )
                    dataset.setncattr(name, value.strip())
        except ForecastDownloadError:
            raise
        except Exception as error:
            raise ForecastDownloadError(
                "Downloaded GloFAS snapshot could not be annotated with request metadata."
            ) from error


GloFASSnapshotIngestionService = GloFASIngestionService
"""Backward-compatible alias for the pre-refinement ingestion service name."""
