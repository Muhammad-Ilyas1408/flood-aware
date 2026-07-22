"""Application composition root for runtime dataset service dependencies."""

from fastapi import FastAPI, Request

from backend.app.config.datasets import DatasetCatalogConfig
from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.services.dependencies import (
    create_dataset_catalog_service,
    create_shelter_service,
    create_village_service,
)
from backend.app.services.protocols import (
    DatasetCatalogServiceProtocol,
    ShelterServiceProtocol,
    VillageServiceProtocol,
)
from backend.app.use_cases.dataset_catalog import ViewDatasetCatalogUseCase
from backend.app.use_cases.protocols import (
    ViewDatasetCatalogUseCaseProtocol,
    ViewSheltersUseCaseProtocol,
    ViewVillagesUseCaseProtocol,
)
from backend.app.use_cases.shelters import ViewSheltersUseCase
from backend.app.use_cases.villages import ViewVillagesUseCase


def configure_dataset_dependencies(
    application: FastAPI,
    configuration: DatasetCatalogConfig,
) -> None:
    """Attach explicit runtime dataset configuration to an application instance.

    Args:
        application: The FastAPI application that owns the runtime configuration.
        configuration: The deployment-supplied village and shelter configurations.
    """
    application.state.dataset_catalog_config = configuration


def get_village_service(request: Request) -> VillageServiceProtocol:
    """Provide a village service constructed from application configuration."""
    configuration = _get_dataset_catalog_config(request)
    village = configuration.villages
    return create_village_service(
        village.dataset_path,
        village.dataset_metadata,
        village.dataset_schema,
    )


def get_shelter_service(request: Request) -> ShelterServiceProtocol:
    """Provide a shelter service constructed from application configuration."""
    configuration = _get_dataset_catalog_config(request)
    shelter = configuration.shelters
    return create_shelter_service(
        shelter.dataset_path,
        shelter.dataset_metadata,
        shelter.dataset_schema,
    )


def get_dataset_catalog_service(request: Request) -> DatasetCatalogServiceProtocol:
    """Provide a dataset catalog service from application configuration."""
    return create_dataset_catalog_service(_get_dataset_catalog_config(request))


def get_village_use_case(request: Request) -> ViewVillagesUseCaseProtocol:
    """Provide the use case for viewing configured village records."""
    return ViewVillagesUseCase(get_village_service(request))


def get_shelter_use_case(request: Request) -> ViewSheltersUseCaseProtocol:
    """Provide the use case for viewing configured shelter records."""
    return ViewSheltersUseCase(get_shelter_service(request))


def get_dataset_catalog_use_case(
    request: Request,
) -> ViewDatasetCatalogUseCaseProtocol:
    """Provide the use case for viewing the configured dataset catalog."""
    return ViewDatasetCatalogUseCase(get_dataset_catalog_service(request))


def _get_dataset_catalog_config(request: Request) -> DatasetCatalogConfig:
    """Return the explicit catalog configuration attached to the application."""
    configuration = getattr(request.app.state, "dataset_catalog_config", None)
    if not isinstance(configuration, DatasetCatalogConfig):
        raise ApplicationConfigurationError(
            "Application dataset dependencies require an explicit DatasetCatalogConfig."
        )
    return configuration
