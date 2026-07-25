"""Manually verify local GloFAS snapshot parsing and forecast-domain mapping."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.forecast.exceptions import ForecastError
from backend.app.forecast.constants import DEFAULT_SNAPSHOT_DIRECTORY
from backend.app.forecast.forecast_tool import GloFASForecastTool
from backend.app.forecast.mapper import ForecastMapper
from backend.app.forecast.models import ForecastResult
from backend.app.forecast.parser import NetCDFForecastParser
from backend.app.forecast.snapshot_locator import SnapshotLocator


_DEFAULT_SWAT_LATITUDE = 34.75
_DEFAULT_SWAT_LONGITUDE = 72.36
_SEPARATOR = "=" * 45


def main() -> int:
    """Load the newest local snapshot and print one readable forecast verification report.

    Returns:
        A process exit code indicating whether local forecast verification succeeded.
    """

    try:
        result = GloFASForecastTool(
            parser=NetCDFForecastParser(),
            mapper=ForecastMapper(),
            snapshot_locator=SnapshotLocator(DEFAULT_SNAPSHOT_DIRECTORY),
        ).get_forecast(_DEFAULT_SWAT_LATITUDE, _DEFAULT_SWAT_LONGITUDE)
    except ForecastError as error:
        print(f"Forecast Tool verification failed.\n{error}")
        return 1
    except Exception:
        print("Forecast Tool verification failed unexpectedly.")
        return 1

    _print_report(result)
    return 0


def _print_report(result: ForecastResult) -> None:
    """Print an immutable forecast result without exposing raw NetCDF data.

    Args:
        result: Validated local GloFAS forecast result returned by the tool.
    """

    discharges = tuple(
        point.discharge_m3_per_second for point in result.series.points
    )
    print(_SEPARATOR)
    print("Flood-Aware Forecast Tool Verification")
    print(_SEPARATOR)
    print()
    print(f"Dataset: {result.metadata.dataset_name}")
    print(f"Reference time: {result.metadata.forecast_reference_time.isoformat()}")
    print(
        "Forecast valid times: "
        + ", ".join(point.valid_time.isoformat() for point in result.series.points)
    )
    print(
        "Lead times: "
        + ", ".join(f"{point.lead_time_hours}h" for point in result.series.points)
    )
    print(f"Number of forecast points: {len(result.series.points)}")
    print(
        "Requested coordinates: "
        f"{result.location.requested_point.latitude}, "
        f"{result.location.requested_point.longitude}"
    )
    print(
        "Selected grid coordinates: "
        f"{result.location.grid_point.latitude}, "
        f"{result.location.grid_point.longitude}"
    )
    print(f"Minimum discharge: {min(discharges):.2f} m³/s")
    print(f"Maximum discharge: {max(discharges):.2f} m³/s")
    print()
    print("Verification Successful")


if __name__ == "__main__":
    raise SystemExit(main())
