"""Manually ingest one small GloFAS NetCDF forecast snapshot for verification."""

import sys
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.forecast.client import GloFASClient
from backend.app.forecast.constants import (
    DEFAULT_DATA_FORMAT,
    DEFAULT_DOWNLOAD_FORMAT,
    DEFAULT_HYDROLOGICAL_MODEL,
    DEFAULT_PRODUCT_TYPE,
    DEFAULT_SWAT_BOUNDING_BOX,
    DEFAULT_SYSTEM_VERSION,
    DEFAULT_VARIABLE,
)
from backend.app.forecast.exceptions import ForecastError
from backend.app.forecast.ingestion import GloFASIngestionService
from backend.app.forecast.settings import ForecastSettings


_SEPARATOR = "=" * 41


def main() -> int:
    """Download and report one raw GloFAS snapshot using configured EWDS credentials.

    Returns:
        A process exit code indicating whether ingestion succeeded.
    """

    started_at = perf_counter()
    request_date = datetime.now(UTC).date()
    client: GloFASClient | None = None
    try:
        settings = ForecastSettings()
        client = GloFASClient(settings)
        service = GloFASIngestionService(client, settings)
        saved_path = service.ingest(forecast_date=request_date)
    except ForecastError as error:
        print(f"GloFAS snapshot ingestion failed.\n{error}")
        return 1
    except Exception:
        print("GloFAS snapshot ingestion failed unexpectedly.")
        return 1
    finally:
        if client is not None:
            client.close()

    elapsed_seconds = perf_counter() - started_at
    _print_report(saved_path, request_date, elapsed_seconds, settings)
    return 0


def _print_report(
    saved_path: Path,
    request_date: date,
    elapsed_seconds: float,
    settings: ForecastSettings,
) -> None:
    """Print a concise manual-verification report.

    Args:
        saved_path: Persisted raw NetCDF snapshot location.
        request_date: UTC GloFAS forecast initialization date.
        elapsed_seconds: Total wall-clock ingestion duration.
        settings: Immutable settings used to construct the ingestion request.
    """

    print(_SEPARATOR)
    print("Flood-Aware GloFAS Snapshot Ingestion")
    print(_SEPARATOR)
    print()
    print(f"Dataset name: {settings.dataset_name}")
    print(f"Product type: {DEFAULT_PRODUCT_TYPE}")
    print(f"Hydrological model: {DEFAULT_HYDROLOGICAL_MODEL}")
    print(f"Variable: {DEFAULT_VARIABLE}")
    print(f"System version: {DEFAULT_SYSTEM_VERSION}")
    print(f"Forecast date: {request_date.isoformat()}")
    print(f"Lead time: {settings.glofas_default_forecast_days * 24} hours")
    print(
        "Bounding box: "
        f"{DEFAULT_SWAT_BOUNDING_BOX.max_latitude}, "
        f"{DEFAULT_SWAT_BOUNDING_BOX.min_longitude}, "
        f"{DEFAULT_SWAT_BOUNDING_BOX.min_latitude}, "
        f"{DEFAULT_SWAT_BOUNDING_BOX.max_longitude}"
    )
    print(f"Output format: {DEFAULT_DATA_FORMAT}")
    print(f"Download format: {DEFAULT_DOWNLOAD_FORMAT}")
    print(f"Saved file: {saved_path}")
    print(f"Download size: {saved_path.stat().st_size} bytes")
    print(f"Elapsed time: {elapsed_seconds:.2f} seconds")
    print()
    print("Verification Successful")


if __name__ == "__main__":
    raise SystemExit(main())
