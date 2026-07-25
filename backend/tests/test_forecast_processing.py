"""Fixture-based tests for local GloFAS NetCDF parsing and domain mapping."""

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

NETCDF_DEPENDENCY_AVAILABLE = False

try:
    from netCDF4 import Dataset
    from pydantic import ValidationError

    from backend.app.forecast.exceptions import (
        ForecastMappingError,
        ForecastParsingError,
        ForecastSnapshotNotFoundError,
    )
    from backend.app.forecast.forecast_tool import GloFASForecastTool
    from backend.app.forecast.mapper import ForecastMapper
    from backend.app.forecast.models import ForecastPoint
    from backend.app.forecast.parser import NetCDFForecastParser
    from backend.app.forecast.snapshot_locator import SnapshotLocator
    from backend.app.gis.geometry import Point
except ModuleNotFoundError:
    pass
else:
    NETCDF_DEPENDENCY_AVAILABLE = True


@unittest.skipIf(
    not NETCDF_DEPENDENCY_AVAILABLE,
    "netCDF4 is not installed in this Python environment.",
)
class ForecastProcessingTests(unittest.TestCase):
    """Verify parser and mapper behavior using only local NetCDF fixtures."""

    def test_parser_extracts_required_forecast_values(self) -> None:
        """A supported control-forecast fixture becomes typed raw parser output."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "valid.nc"
            )
            parsed = NetCDFForecastParser().parse(snapshot_path)

        self.assertEqual(parsed.dataset_name, "cems-glofas-forecast")
        self.assertEqual(parsed.forecast_reference_time, _reference_time())
        self.assertEqual(parsed.lead_time_hours, (24, 48))
        self.assertEqual(
            parsed.valid_times,
            (
                datetime(2026, 7, 26, tzinfo=UTC),
                datetime(2026, 7, 27, tzinfo=UTC),
            ),
        )
        self.assertEqual(parsed.discharge_values[1][1][1], 80.0)

    def test_parser_supports_glofas_forecast_period_layout(self) -> None:
        """The parser accepts the temporal layout emitted by GloFAS NetCDF snapshots."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "glofas_layout.nc",
                glofas_layout=True,
            )
            parsed = NetCDFForecastParser().parse(snapshot_path)

        self.assertEqual(parsed.lead_time_hours, (24,))
        self.assertEqual(parsed.valid_times, (datetime(2026, 7, 26, tzinfo=UTC),))
        self.assertEqual(parsed.discharge_values[0][1][1], 40.0)

    def test_mapper_selects_nearest_grid_and_preserves_series_order(self) -> None:
        """Mapping reuses GIS distance logic and preserves valid-time ordering."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "valid.nc"
            )
            parsed = NetCDFForecastParser().parse(snapshot_path)
            result = ForecastMapper().map(
                parsed,
                Point(latitude=34.91, longitude=72.19),
            )

        self.assertEqual(result.location.requested_point.latitude, 34.91)
        self.assertEqual(result.location.grid_point.latitude, 34.9)
        self.assertEqual(result.location.grid_point.longitude, 72.2)
        self.assertEqual(
            tuple(point.lead_time_hours for point in result.series.points),
            (24, 48),
        )
        self.assertEqual(
            tuple(point.discharge_m3_per_second for point in result.series.points),
            (10.0, 50.0),
        )

    def test_forecast_domain_models_are_immutable(self) -> None:
        """Mapped point models remain immutable after construction."""

        point = ForecastPoint(
            valid_time=datetime(2026, 7, 26, tzinfo=UTC),
            lead_time_hours=24,
            discharge_m3_per_second=10.0,
        )
        with self.assertRaises(ValidationError):
            point.discharge_m3_per_second = 20.0

    def test_parser_rejects_missing_discharge_variable(self) -> None:
        """Snapshots without river discharge fail through the forecast exception hierarchy."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "missing_discharge.nc",
                include_discharge=False,
            )
            with self.assertRaises(ForecastParsingError):
                NetCDFForecastParser().parse(snapshot_path)

    def test_parser_rejects_unsupported_discharge_dimensions(self) -> None:
        """Snapshots without the supported control-forecast dimensions are rejected."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "unsupported.nc",
                supported_dimensions=False,
            )
            with self.assertRaises(ForecastParsingError):
                NetCDFForecastParser().parse(snapshot_path)

    def test_parser_rejects_missing_required_metadata(self) -> None:
        """Required GloFAS provenance is never inferred from ingestion defaults."""

        for attribute in (
            "dataset_name",
            "product_type",
            "hydrological_model",
            "system_version",
        ):
            with (
                self.subTest(attribute=attribute),
                TemporaryDirectory() as temporary_directory,
            ):
                snapshot_path = _create_snapshot_fixture(
                    Path(temporary_directory) / f"missing_{attribute}.nc",
                    missing_metadata_attribute=attribute,
                )
                with self.assertRaisesRegex(
                    ForecastParsingError,
                    f"Missing required metadata attribute: {attribute}",
                ):
                    NetCDFForecastParser().parse(snapshot_path)

    def test_parser_rejects_whitespace_only_required_metadata(self) -> None:
        """Blank provenance values are rejected rather than silently normalized to defaults."""

        with TemporaryDirectory() as temporary_directory:
            snapshot_path = _create_snapshot_fixture(
                Path(temporary_directory) / "blank_metadata.nc",
                metadata_overrides={"product_type": "   "},
            )
            with self.assertRaisesRegex(
                ForecastParsingError,
                "Missing required metadata attribute: product_type",
            ):
                NetCDFForecastParser().parse(snapshot_path)

    def test_snapshot_locator_rejects_missing_or_empty_directories(self) -> None:
        """Snapshot discovery reports both absent and empty ingestion locations precisely."""

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            with self.assertRaises(ForecastSnapshotNotFoundError):
                SnapshotLocator(directory / "missing").newest_snapshot()
            with self.assertRaises(ForecastSnapshotNotFoundError):
                SnapshotLocator(directory).newest_snapshot()

    def test_snapshot_locator_uses_mtime_then_filename_tie_breaker(self) -> None:
        """Snapshot discovery retains the established deterministic selection rule."""

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            older = directory / "glofas_control_older.nc"
            tied_first = directory / "glofas_control_a.nc"
            tied_last = directory / "glofas_control_b.nc"
            for snapshot in (older, tied_first, tied_last):
                snapshot.touch()
            os.utime(older, (1_700_000_000, 1_700_000_000))
            os.utime(tied_first, (1_700_000_100, 1_700_000_100))
            os.utime(tied_last, (1_700_000_100, 1_700_000_100))

            selected = SnapshotLocator(directory).newest_snapshot()

        self.assertEqual(selected, tied_last)

    def test_tool_loads_newest_local_snapshot(self) -> None:
        """The Forecast Tool maps only the newest persisted NetCDF snapshot."""

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            older_snapshot = _create_snapshot_fixture(
                directory / "glofas_control_older.nc"
            )
            newer_snapshot = _create_snapshot_fixture(
                directory / "glofas_control_newer.nc"
            )
            os.utime(older_snapshot, (1_700_000_000, 1_700_000_000))
            os.utime(newer_snapshot, (1_700_000_100, 1_700_000_100))

            result = GloFASForecastTool(
                parser=NetCDFForecastParser(),
                mapper=ForecastMapper(),
                snapshot_locator=SnapshotLocator(directory),
            ).get_forecast(34.91, 72.19)

        self.assertEqual(result.metadata.snapshot_path, newer_snapshot)
        self.assertEqual(result.series.points[0].discharge_m3_per_second, 10.0)

    def test_tool_rejects_missing_snapshots_and_invalid_coordinates(self) -> None:
        """Tool translates local-storage and coordinate validation failures precisely."""

        with TemporaryDirectory() as temporary_directory:
            tool = GloFASForecastTool(
                parser=NetCDFForecastParser(),
                mapper=ForecastMapper(),
                snapshot_locator=SnapshotLocator(Path(temporary_directory)),
            )
            with self.assertRaises(ForecastSnapshotNotFoundError):
                tool.get_forecast(34.75, 72.36)
            with self.assertRaises(ForecastMappingError):
                tool.get_forecast(91.0, 72.36)


def _reference_time() -> datetime:
    """Return the fixed reference time represented by all local test fixtures."""

    return datetime(2026, 7, 25, tzinfo=UTC)


def _create_snapshot_fixture(
    snapshot_path: Path,
    *,
    include_discharge: bool = True,
    supported_dimensions: bool = True,
    glofas_layout: bool = False,
    missing_metadata_attribute: str | None = None,
    metadata_overrides: dict[str, str] | None = None,
) -> Path:
    """Create a compact local NetCDF control-forecast fixture.

    Args:
        snapshot_path: Local file path for the generated fixture.
        include_discharge: Whether to create the required GloFAS discharge variable.
        supported_dimensions: Whether to use the supported four-dimensional layout.
        glofas_layout: Whether to use the official forecast-period temporal layout.
        missing_metadata_attribute: Required provenance attribute to omit from the fixture.
        metadata_overrides: Replacement values for fixture provenance attributes.

    Returns:
        The generated fixture path.
    """

    with Dataset(snapshot_path, mode="w") as dataset:
        dataset.createDimension("time", 1)
        dataset.createDimension("step", 2)
        if glofas_layout:
            dataset.createDimension("forecast_period", 1)
            dataset.createDimension("forecast_reference_time", 1)
        dataset.createDimension("latitude", 2)
        dataset.createDimension("longitude", 2)
        metadata = {
            "dataset_name": "cems-glofas-forecast",
            "product_type": "control_forecast",
            "hydrological_model": "lisflood",
            "system_version": "operational",
        }
        metadata.update(metadata_overrides or {})
        for attribute, value in metadata.items():
            if attribute != missing_metadata_attribute:
                setattr(dataset, attribute, value)

        if glofas_layout:
            reference_time = dataset.createVariable(
                "forecast_reference_time",
                "f8",
                ("forecast_reference_time",),
            )
            reference_time.units = "seconds since 1970-01-01"
            reference_time[:] = [int(_reference_time().timestamp())]
            forecast_period = dataset.createVariable(
                "forecast_period",
                "f8",
                ("forecast_period",),
            )
            forecast_period.units = "hours"
            forecast_period[:] = [24]
            valid_time = dataset.createVariable("valid_time", "f8")
            valid_time.units = "seconds since 1970-01-01"
            valid_time.assignValue(int(datetime(2026, 7, 26, tzinfo=UTC).timestamp()))
        else:
            time = dataset.createVariable("time", "f8", ("time",))
            time.units = "hours since 2026-07-25 00:00:00"
            time[:] = [0]
            step = dataset.createVariable("step", "f8", ("step",))
            step.units = "hours"
            step[:] = [24, 48]
            valid_time = dataset.createVariable("valid_time", "f8", ("step",))
            valid_time.units = "hours since 2026-07-25 00:00:00"
            valid_time[:] = [24, 48]
        latitude = dataset.createVariable("latitude", "f8", ("latitude",))
        latitude[:] = [34.9, 35.0]
        longitude = dataset.createVariable("longitude", "f8", ("longitude",))
        longitude[:] = [72.2, 72.3]

        if include_discharge:
            dimensions = (
                (
                    "forecast_period",
                    "forecast_reference_time",
                    "latitude",
                    "longitude",
                )
                if glofas_layout
                else (
                    ("time", "step", "latitude", "longitude")
                    if supported_dimensions
                    else ("time", "latitude", "longitude")
                )
            )
            discharge = dataset.createVariable("dis24", "f8", dimensions)
            if glofas_layout:
                discharge[:] = [[[[10.0, 20.0], [30.0, 40.0]]]]
            elif supported_dimensions:
                discharge[:] = [
                    [[[10.0, 20.0], [30.0, 40.0]], [[50.0, 60.0], [70.0, 80.0]]]
                ]
            else:
                discharge[:] = [[[10.0, 20.0], [30.0, 40.0]]]
    return snapshot_path
