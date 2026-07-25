"""Unit tests for the isolated GloFAS raw snapshot ingestion pipeline."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

FORECAST_DEPENDENCIES_AVAILABLE = False

try:
    import cdsapi
    from netCDF4 import Dataset
    from pydantic import ValidationError

    from backend.app.forecast.client import GloFASClient
    from backend.app.forecast.constants import (
        DEFAULT_DATASET_NAME,
        DEFAULT_HYDROLOGICAL_MODEL,
        DEFAULT_PRODUCT_TYPE,
        DEFAULT_SWAT_BOUNDING_BOX,
        DEFAULT_SYSTEM_VERSION,
        DEFAULT_VARIABLE,
    )
    from backend.app.forecast.exceptions import (
        ForecastAuthenticationError,
        ForecastConfigurationError,
        ForecastDownloadError,
        ForecastTimeoutError,
    )
    from backend.app.forecast.ingestion import GloFASIngestionService
    from backend.app.forecast.settings import ForecastSettings
except ModuleNotFoundError:
    pass
else:
    FORECAST_DEPENDENCIES_AVAILABLE = True


@unittest.skipIf(
    not FORECAST_DEPENDENCIES_AVAILABLE,
    "cdsapi is not installed in this Python environment.",
)
class GloFASIngestionTests(unittest.TestCase):
    """Verify GloFAS requests and local snapshot handling without live downloads."""

    def test_settings_validate_timeout_and_forecast_days(self) -> None:
        """Settings reject invalid timing configuration before requests are made."""

        with self.assertRaises(ValidationError):
            ForecastSettings(GLOFAS_REQUEST_TIMEOUT=0)
        with self.assertRaises(ValidationError):
            ForecastSettings(GLOFAS_DEFAULT_FORECAST_DAYS=31)
        with self.assertRaises(ValidationError):
            ForecastSettings(
                GLOFAS_BASE_URL="url: https://ewds.climate.copernicus.eu/api"
            )

    def test_client_requires_api_key(self) -> None:
        """Client construction rejects missing EWDS authentication."""

        with self.assertRaises(ForecastConfigurationError):
            GloFASClient(ForecastSettings(GLOFAS_API_KEY=None))

    def test_client_translates_provider_errors(self) -> None:
        """Provider messages become forecast-specific exceptions."""

        client = MagicMock()
        client.retrieve.side_effect = Exception("401 Unauthorized")
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ForecastAuthenticationError):
                GloFASClient(_settings(), client).download_snapshot(
                    {"variable": "river_discharge_in_the_last_24_hours"},
                    Path(temporary_directory) / "snapshot.nc",
                )

        client.retrieve.side_effect = TimeoutError("request timeout")
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ForecastTimeoutError):
                GloFASClient(_settings(), client).download_snapshot(
                    {"variable": "river_discharge_in_the_last_24_hours"},
                    Path(temporary_directory) / "snapshot.nc",
                )

    def test_ingestion_writes_one_deterministic_snapshot_and_request(self) -> None:
        """Ingestion builds the request and persists its exact provenance metadata."""

        cds_client = MagicMock()

        def write_snapshot(
            name: str,
            request: dict[str, object],
            target: str,
        ) -> None:
            self.assertEqual(name, "custom-glofas-dataset")
            with Dataset(target, mode="w"):
                pass

        cds_client.retrieve.side_effect = write_snapshot
        with TemporaryDirectory() as temporary_directory:
            settings = _settings(GLOFAS_DATASET_NAME="custom-glofas-dataset")
            service = GloFASIngestionService(
                GloFASClient(settings, cds_client),
                settings,
                Path(temporary_directory),
            )
            saved_path = service.ingest(
                forecast_date=date(2026, 7, 25),
                ingested_at=datetime(2026, 7, 25, 8, 12, 41, tzinfo=UTC),
            )

            self.assertEqual(saved_path.name, "glofas_control_20260725T081241Z.nc")
            with Dataset(saved_path, mode="r") as dataset:
                self.assertEqual(dataset.dataset_name, "custom-glofas-dataset")
                self.assertEqual(dataset.product_type, DEFAULT_PRODUCT_TYPE)
                self.assertEqual(dataset.hydrological_model, DEFAULT_HYDROLOGICAL_MODEL)
                self.assertEqual(dataset.system_version, DEFAULT_SYSTEM_VERSION)
            request = cds_client.retrieve.call_args.args[1]
            self.assertEqual(request["system_version"], DEFAULT_SYSTEM_VERSION)
            self.assertEqual(request["hydrological_model"], DEFAULT_HYDROLOGICAL_MODEL)
            self.assertEqual(request["product_type"], DEFAULT_PRODUCT_TYPE)
            self.assertEqual(request["variable"], DEFAULT_VARIABLE)
            self.assertEqual(
                request["area"],
                [
                    DEFAULT_SWAT_BOUNDING_BOX.max_latitude,
                    DEFAULT_SWAT_BOUNDING_BOX.min_longitude,
                    DEFAULT_SWAT_BOUNDING_BOX.min_latitude,
                    DEFAULT_SWAT_BOUNDING_BOX.max_longitude,
                ],
            )
            self.assertEqual(request["leadtime_hour"], ["24"])
            self.assertEqual(request["data_format"], "netcdf")
            self.assertEqual(request["download_format"], "unarchived")

    def test_ingestion_never_overwrites_existing_snapshot(self) -> None:
        """Existing deterministic filenames remain protected from replacement."""

        cds_client = MagicMock()
        with TemporaryDirectory() as temporary_directory:
            storage = Path(temporary_directory)
            target = storage / "glofas_control_20260725T081241Z.nc"
            target.write_bytes(b"existing")
            service = GloFASIngestionService(
                GloFASClient(_settings(), cds_client),
                _settings(),
                storage,
            )

            with self.assertRaises(ForecastDownloadError):
                service.ingest(
                    forecast_date=date(2026, 7, 25),
                    ingested_at=datetime(2026, 7, 25, 8, 12, 41, tzinfo=UTC),
                )
            cds_client.retrieve.assert_not_called()

    def test_client_closes_only_its_own_session(self) -> None:
        """Client ownership rules protect injected CDS client resources."""

        owned_client = MagicMock()
        owned_client.session = MagicMock()
        with patch(
            "backend.app.forecast.client.cdsapi.Client", return_value=owned_client
        ):
            client = GloFASClient(_settings())
        client.close()
        owned_client.session.close.assert_called_once_with()

        injected_client = MagicMock()
        injected_client.session = MagicMock()
        GloFASClient(_settings(), injected_client).close()
        injected_client.session.close.assert_not_called()

    def test_constants_define_default_dataset_and_swat_bounds(self) -> None:
        """Static GloFAS defaults are centralized outside ingestion business logic."""

        self.assertEqual(DEFAULT_DATASET_NAME, "cems-glofas-forecast")
        self.assertTrue(
            DEFAULT_SWAT_BOUNDING_BOX.contains(DEFAULT_SWAT_BOUNDING_BOX.center())
        )


def _settings(**overrides: object) -> ForecastSettings:
    """Return deterministic GloFAS configuration for isolated tests."""

    values: dict[str, object] = {
        "GLOFAS_API_KEY": "test-personal-access-token",
        "GLOFAS_BASE_URL": "https://ewds.test/api",
        "GLOFAS_REQUEST_TIMEOUT": 10,
        "GLOFAS_DEFAULT_FORECAST_DAYS": 1,
    }
    values.update(overrides)
    return ForecastSettings(**values)
