"""Integration-style tests for repository, service, dependency, and API composition."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import FastAPI, Request

from backend.app.composition import (
    get_dataset_catalog_service,
    get_shelter_service,
    get_village_service,
)
from backend.app.config.datasets import DatasetCatalogConfig
from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.data.exceptions import DatasetFormatError, DatasetValidationError
from backend.app.data.file_support import DatasetFileFormat
from backend.app.data.models import (
    DatasetColumn,
    DatasetColumnType,
    DatasetMetadata,
    DatasetSchema,
    DatasetTable,
)
from backend.app.data.repositories import CSVRepository, GeoJSONRepository
from backend.app.data.repository_config import FileRepositoryConfig
from backend.app.dtos.datasets import ShelterListDTO, VillageListDTO
from backend.app.services.dependencies import (
    create_dataset_catalog_service,
    create_dataset_service,
    create_shelter_service,
    create_village_service,
)
from backend.app.services.services import (
    DatasetCatalogService,
    DatasetService,
    ShelterService,
    VillageService,
)
from backend.app.schemas.datasets import (
    DatasetCatalogResponse,
    ShelterListResponse,
    VillageListResponse,
)
from backend.app.main import create_application


FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
EXPECTED_RECORD_COUNT = 10


async def _get_application_response(
    application: FastAPI,
    path: str,
) -> tuple[int, bytes]:
    """Execute a GET request against the ASGI application without external clients."""

    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        """Provide the single empty HTTP request body."""

        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        """Collect ASGI response messages emitted by the application."""

        messages.append(message)

    await application(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    status_code = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    body = b"".join(
        message["body"]
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(status_code), body


def _dataset_metadata(name: str) -> DatasetMetadata:
    """Build explicit metadata required by a file repository configuration."""

    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return DatasetMetadata(
        name=name,
        description="Service-layer integration test dataset.",
        version="1.0.0",
        source="test fixture",
        created_at=timestamp,
        updated_at=timestamp,
    )


def _village_schema() -> DatasetSchema:
    """Build the explicit schema used by the village fixture dataset."""

    return DatasetSchema(
        columns=(
            DatasetColumn(
                name="name",
                data_type=DatasetColumnType.STRING,
                nullable=False,
            ),
            DatasetColumn(
                name="district",
                data_type=DatasetColumnType.STRING,
                nullable=False,
            ),
            DatasetColumn(
                name="population",
                data_type=DatasetColumnType.INTEGER,
                nullable=False,
            ),
        )
    )


def _shelter_schema() -> DatasetSchema:
    """Build the explicit schema used by the shelter fixture dataset."""

    return DatasetSchema(
        columns=(
            DatasetColumn(
                name="name",
                data_type=DatasetColumnType.STRING,
                nullable=False,
            ),
            DatasetColumn(
                name="district",
                data_type=DatasetColumnType.STRING,
                nullable=False,
            ),
            DatasetColumn(
                name="capacity",
                data_type=DatasetColumnType.INTEGER,
                nullable=False,
            ),
        )
    )


def _csv_repository(
    filename: str,
    metadata: DatasetMetadata,
    schema: DatasetSchema,
) -> CSVRepository:
    """Construct a CSV repository over one existing fixture file."""

    return CSVRepository(
        FileRepositoryConfig(
            dataset_path=str(FIXTURES_DIRECTORY / filename),
            dataset_metadata=metadata,
            dataset_schema=schema,
            file_format=DatasetFileFormat.CSV,
        )
    )


def _geojson_repository(
    filename: str,
    metadata: DatasetMetadata,
    schema: DatasetSchema,
) -> GeoJSONRepository:
    """Construct a GeoJSON repository over one existing fixture file."""

    return GeoJSONRepository(
        FileRepositoryConfig(
            dataset_path=str(FIXTURES_DIRECTORY / filename),
            dataset_metadata=metadata,
            dataset_schema=schema,
            file_format=DatasetFileFormat.GEOJSON,
        )
    )


def _dataset_catalog_configuration() -> DatasetCatalogConfig:
    """Build explicit fixture configuration for composition tests."""

    return DatasetCatalogConfig(
        villages=FileRepositoryConfig(
            dataset_path=str(FIXTURES_DIRECTORY / "villages.csv"),
            dataset_metadata=_dataset_metadata("Village catalog fixture"),
            dataset_schema=_village_schema(),
            file_format=DatasetFileFormat.CSV,
        ),
        shelters=FileRepositoryConfig(
            dataset_path=str(FIXTURES_DIRECTORY / "shelters.csv"),
            dataset_metadata=_dataset_metadata("Shelter catalog fixture"),
            dataset_schema=_shelter_schema(),
            file_format=DatasetFileFormat.CSV,
        ),
    )


class RepositoryTests(unittest.TestCase):
    """Verify concrete repositories load the approved fixture datasets."""

    def test_csv_repository_loads_village_fixture(self) -> None:
        """CSV repositories return validated tables and configured metadata."""

        metadata = _dataset_metadata("Village CSV fixture")
        repository = _csv_repository("villages.csv", metadata, _village_schema())

        repository.validate()
        table = repository.load()

        self.assertIsInstance(table, DatasetTable)
        self.assertEqual(len(table.rows), EXPECTED_RECORD_COUNT)
        self.assertEqual(repository.metadata(), metadata)

    def test_geojson_repository_loads_village_fixture(self) -> None:
        """GeoJSON repositories return validated tables and configured metadata."""

        metadata = _dataset_metadata("Village GeoJSON fixture")
        repository = _geojson_repository(
            "villages.geojson",
            metadata,
            _village_schema(),
        )

        repository.validate()
        table = repository.load()

        self.assertIsInstance(table, DatasetTable)
        self.assertEqual(len(table.rows), EXPECTED_RECORD_COUNT)
        self.assertEqual(repository.metadata(), metadata)


class ServiceTests(unittest.TestCase):
    """Verify services orchestrate repository loading without extra behavior."""

    def test_dataset_service_loads_csv_repository_result(self) -> None:
        """DatasetService delegates loading to a CSV-backed repository."""

        repository = _csv_repository(
            "villages.csv",
            _dataset_metadata("Village CSV service fixture"),
            _village_schema(),
        )

        table = DatasetService(repository).load_dataset()

        self.assertIsInstance(table, DatasetTable)
        self.assertEqual(len(table.rows), EXPECTED_RECORD_COUNT)

    def test_dataset_service_loads_geojson_repository_result(self) -> None:
        """DatasetService accepts a GeoJSON repository through the table protocol."""

        repository = _geojson_repository(
            "villages.geojson",
            _dataset_metadata("Village GeoJSON service fixture"),
            _village_schema(),
        )

        table = DatasetService(repository).load_dataset()

        self.assertIsInstance(table, DatasetTable)
        self.assertEqual(len(table.rows), EXPECTED_RECORD_COUNT)

    def test_village_service_loads_village_repository(self) -> None:
        """VillageService delegates through its composed DatasetService."""

        repository = _csv_repository(
            "villages.csv",
            _dataset_metadata("Village service fixture"),
            _village_schema(),
        )

        response = VillageService(repository).load_villages()

        self.assertIsInstance(response, VillageListDTO)
        self.assertEqual(len(response.villages), EXPECTED_RECORD_COUNT)

    def test_shelter_service_loads_shelter_repository(self) -> None:
        """ShelterService delegates through its composed DatasetService."""

        repository = _csv_repository(
            "shelters.csv",
            _dataset_metadata("Shelter service fixture"),
            _shelter_schema(),
        )

        response = ShelterService(repository).load_shelters()

        self.assertIsInstance(response, ShelterListDTO)
        self.assertEqual(len(response.shelters), EXPECTED_RECORD_COUNT)

    def test_dataset_service_returns_exact_summary(self) -> None:
        """DatasetService derives summary statistics from the loaded table."""

        metadata = _dataset_metadata("Village summary fixture")
        repository = _csv_repository("villages.csv", metadata, _village_schema())

        summary = DatasetService(repository).load_summary()

        self.assertEqual(summary.metadata, metadata)
        self.assertEqual(summary.statistics.record_count, EXPECTED_RECORD_COUNT)


class DependencyFactoryTests(unittest.TestCase):
    """Verify dependency factories construct correctly wired services."""

    def test_dataset_service_factory_accepts_geojson_repository(self) -> None:
        """The generic factory returns a service that loads GeoJSON data."""

        repository = _geojson_repository(
            "villages.geojson",
            _dataset_metadata("Dataset factory fixture"),
            _village_schema(),
        )

        service = create_dataset_service(repository)

        self.assertIsInstance(service, DatasetService)
        self.assertEqual(len(service.load_dataset().rows), EXPECTED_RECORD_COUNT)

    def test_village_service_factory_constructs_csv_service(self) -> None:
        """The village factory builds a service that loads the village fixture."""

        service = create_village_service(
            str(FIXTURES_DIRECTORY / "villages.csv"),
            _dataset_metadata("Village factory fixture"),
            _village_schema(),
        )

        self.assertIsInstance(service, VillageService)
        self.assertEqual(len(service.load_villages().villages), EXPECTED_RECORD_COUNT)

    def test_shelter_service_factory_constructs_csv_service(self) -> None:
        """The shelter factory builds a service that loads the shelter fixture."""

        service = create_shelter_service(
            str(FIXTURES_DIRECTORY / "shelters.csv"),
            _dataset_metadata("Shelter factory fixture"),
            _shelter_schema(),
        )

        self.assertIsInstance(service, ShelterService)
        self.assertEqual(len(service.load_shelters().shelters), EXPECTED_RECORD_COUNT)

    def test_catalog_service_factory_constructs_independent_summaries(self) -> None:
        """The catalog factory returns separate village and shelter summaries."""

        configuration = _dataset_catalog_configuration()

        service = create_dataset_catalog_service(configuration)
        catalog = service.load_catalog()

        self.assertIsInstance(service, DatasetCatalogService)
        self.assertEqual(catalog.villages.statistics.record_count, EXPECTED_RECORD_COUNT)
        self.assertEqual(catalog.shelters.statistics.record_count, EXPECTED_RECORD_COUNT)


class ApiSchemaTranslationTests(unittest.TestCase):
    """Verify API schemas translate service DTOs without service schema imports."""

    def test_village_and_shelter_response_translation(self) -> None:
        """List response schemas preserve records from application DTOs."""

        village_dto = VillageService(
            _csv_repository(
                "villages.csv",
                _dataset_metadata("Village schema translation fixture"),
                _village_schema(),
            )
        ).load_villages()
        shelter_dto = ShelterService(
            _csv_repository(
                "shelters.csv",
                _dataset_metadata("Shelter schema translation fixture"),
                _shelter_schema(),
            )
        ).load_shelters()

        village_response = VillageListResponse.from_dto(village_dto)
        shelter_response = ShelterListResponse.from_dto(shelter_dto)

        self.assertEqual(len(village_response.data), EXPECTED_RECORD_COUNT)
        self.assertEqual(len(shelter_response.data), EXPECTED_RECORD_COUNT)

    def test_catalog_response_translation_uses_named_datasets(self) -> None:
        """Catalog response exposes village and shelter summaries by name."""

        configuration = _dataset_catalog_configuration()
        catalog_dto = create_dataset_catalog_service(configuration).load_catalog()

        response = DatasetCatalogResponse.from_dto(catalog_dto)

        self.assertEqual(response.villages.statistics.record_count, EXPECTED_RECORD_COUNT)
        self.assertEqual(response.shelters.statistics.record_count, EXPECTED_RECORD_COUNT)


class CompositionRootTests(unittest.TestCase):
    """Verify application composition wires only explicit runtime dependencies."""

    def test_dependency_providers_construct_configured_services(self) -> None:
        """Providers construct services through the application-held configuration."""

        configuration = _dataset_catalog_configuration()
        application = create_application(configuration)
        request = Request({"type": "http", "app": application})

        self.assertIsInstance(get_village_service(request), VillageService)
        self.assertIsInstance(get_shelter_service(request), ShelterService)
        self.assertIsInstance(
            get_dataset_catalog_service(request),
            DatasetCatalogService,
        )

    def test_dependency_providers_require_explicit_configuration(self) -> None:
        """Providers reject applications without deployment-supplied configuration."""

        request = Request({"type": "http", "app": create_application()})

        with self.assertRaisesRegex(
            ApplicationConfigurationError,
            "Application dataset dependencies require an explicit DatasetCatalogConfig.",
        ):
            get_village_service(request)


class ApiEndpointTests(unittest.TestCase):
    """Verify API endpoints coordinate dependencies, services, and schemas."""

    def setUp(self) -> None:
        """Create an application with explicit fixture-backed configuration."""

        self.application = create_application(_dataset_catalog_configuration())
        self.unconfigured_application = create_application()

    def _assert_configuration_failure(self, path: str) -> None:
        """Assert a missing runtime configuration returns the global error response."""

        status_code, body = asyncio.run(
            _get_application_response(self.unconfigured_application, path)
        )

        self.assertEqual(status_code, 500)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["status_code"], 500)
        self.assertEqual(payload["detail"], "An unexpected server error occurred.")
        self.assertEqual(payload["path"], path)
        self.assertIn("request_id", payload)

    def test_get_villages_returns_configured_response(self) -> None:
        """The villages endpoint returns the translated village response schema."""

        status_code, body = asyncio.run(
            _get_application_response(self.application, "/villages")
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["data"]), EXPECTED_RECORD_COUNT)
        self.assertEqual(payload["data"][0]["name"], "Akora Khattak")

    def test_get_shelters_returns_configured_response(self) -> None:
        """The shelters endpoint returns the translated shelter response schema."""

        status_code, body = asyncio.run(
            _get_application_response(self.application, "/shelters")
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["data"]), EXPECTED_RECORD_COUNT)
        self.assertEqual(payload["data"][0]["name"], "Government High School Akora")

    def test_get_dataset_catalog_returns_named_summaries(self) -> None:
        """The catalog endpoint returns independent named dataset summaries."""

        status_code, body = asyncio.run(
            _get_application_response(self.application, "/datasets/catalog")
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(
            payload["villages"]["statistics"]["record_count"],
            EXPECTED_RECORD_COUNT,
        )
        self.assertEqual(
            payload["shelters"]["statistics"]["record_count"],
            EXPECTED_RECORD_COUNT,
        )

    def test_get_villages_returns_global_error_for_missing_configuration(self) -> None:
        """The villages endpoint exposes the centralized configuration failure response."""

        self._assert_configuration_failure("/villages")

    def test_get_shelters_returns_global_error_for_missing_configuration(self) -> None:
        """The shelters endpoint exposes the centralized configuration failure response."""

        self._assert_configuration_failure("/shelters")

    def test_get_dataset_catalog_returns_global_error_for_missing_configuration(self) -> None:
        """The catalog endpoint exposes the centralized configuration failure response."""

        self._assert_configuration_failure("/datasets/catalog")

    def test_openapi_registers_dataset_endpoints(self) -> None:
        """OpenAPI exposes the three read-only dataset endpoints."""

        status_code, body = asyncio.run(
            _get_application_response(self.application, "/openapi.json")
        )

        self.assertEqual(status_code, 200)
        paths = json.loads(body)["paths"]
        self.assertIn("/villages", paths)
        self.assertIn("/shelters", paths)
        self.assertIn("/datasets/catalog", paths)
        self.assertEqual(paths["/villages"]["get"]["operationId"], "getVillages")
        self.assertEqual(paths["/shelters"]["get"]["operationId"], "getShelters")
        self.assertEqual(
            paths["/datasets/catalog"]["get"]["operationId"],
            "getDatasetCatalog",
        )
        self.assertIn("500", paths["/villages"]["get"]["responses"])
        self.assertIn("500", paths["/shelters"]["get"]["responses"])
        self.assertIn("500", paths["/datasets/catalog"]["get"]["responses"])

    def test_docs_loads(self) -> None:
        """Swagger UI remains available after dataset route registration."""

        status_code, _ = asyncio.run(
            _get_application_response(self.application, "/docs")
        )

        self.assertEqual(status_code, 200)


class NegativeRepositoryTests(unittest.TestCase):
    """Verify existing configuration and format validation remains unchanged."""

    def test_configuration_rejects_wrong_file_format(self) -> None:
        """Repository configuration rejects a declared format that mismatches a path."""

        with self.assertRaisesRegex(
            DatasetValidationError,
            "Repository configuration file format must match the dataset path extension.",
        ):
            FileRepositoryConfig(
                dataset_path=str(FIXTURES_DIRECTORY / "villages.csv"),
                dataset_metadata=_dataset_metadata("Wrong format fixture"),
                dataset_schema=_village_schema(),
                file_format=DatasetFileFormat.GEOJSON,
            )

    def test_csv_repository_rejects_schema_mismatch(self) -> None:
        """CSV loading retains existing schema mismatch validation."""

        mismatched_schema = DatasetSchema(
            columns=(
                DatasetColumn(
                    name="unexpected",
                    data_type=DatasetColumnType.STRING,
                    nullable=False,
                ),
            )
        )
        repository = _csv_repository(
            "villages.csv",
            _dataset_metadata("CSV schema mismatch fixture"),
            mismatched_schema,
        )

        with self.assertRaisesRegex(
            DatasetValidationError,
            "CSV headers must match the supplied schema.",
        ):
            repository.load()

    def test_csv_repository_rejects_malformed_csv(self) -> None:
        """CSV loading retains existing malformed CSV validation."""

        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "malformed.csv"
            path.write_text(
                "name,district,population\n\"unterminated,Swat,1000\n",
                encoding="utf-8",
            )
            repository = CSVRepository(
                FileRepositoryConfig(
                    dataset_path=str(path),
                    dataset_metadata=_dataset_metadata("Malformed CSV fixture"),
                    dataset_schema=_village_schema(),
                    file_format=DatasetFileFormat.CSV,
                )
            )

            with self.assertRaisesRegex(DatasetFormatError, "CSV input is malformed."):
                repository.load()

    def test_geojson_repository_rejects_malformed_geojson(self) -> None:
        """GeoJSON validation retains existing FeatureCollection requirements."""

        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "malformed.geojson"
            path.write_text('{"type":"FeatureCollection"}', encoding="utf-8")
            repository = GeoJSONRepository(
                FileRepositoryConfig(
                    dataset_path=str(path),
                    dataset_metadata=_dataset_metadata("Malformed GeoJSON fixture"),
                    dataset_schema=_village_schema(),
                    file_format=DatasetFileFormat.GEOJSON,
                )
            )

            with self.assertRaisesRegex(
                DatasetFormatError,
                "GeoJSON dataset must be a valid FeatureCollection.",
            ):
                repository.validate()


if __name__ == "__main__":
    unittest.main()
