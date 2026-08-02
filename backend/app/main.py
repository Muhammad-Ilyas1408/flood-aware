"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from backend.app.api.router import api_router
from backend.app.composition import configure_dataset_dependencies
from backend.app.config.datasets import (
    DatasetCatalogConfig,
    create_production_dataset_catalog_config,
)
from backend.app.config.graph_dependencies import (
    close_graph_dependencies,
    configure_graph_dependencies,
)
from backend.app.config.logging import configure_logging
from backend.app.config.settings import Settings, get_settings
from backend.app.conversation import ConversationOrchestrator
from backend.app.conversation.exceptions import ConversationSessionNotFoundError
from backend.app.core.application_exceptions import ApplicationError
from backend.app.core.exceptions import (
    handle_application_exception,
    handle_conversation_session_not_found_error,
    handle_decision_generation_error,
    handle_http_exception,
    handle_request_validation_error,
    handle_unexpected_exception,
    handle_validation_exception,
)
from backend.app.core.logger import get_logger
from backend.app.core.validation_exceptions import ValidationException
from backend.app.decision.exceptions import DecisionGenerationError
from backend.app.middleware.request_logging import log_request

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""

    settings: Settings = get_settings()
    logger.info(
        "Starting %s version %s in %s environment.",
        settings.application_name,
        settings.version,
        settings.environment.value,
    )
    if not isinstance(
        getattr(application.state, "dataset_catalog_config", None),
        DatasetCatalogConfig,
    ):
        configure_dataset_dependencies(
            application,
            create_production_dataset_catalog_config(),
        )
    if not isinstance(
        getattr(application.state, "conversation_orchestrator", None),
        ConversationOrchestrator,
    ):
        configure_graph_dependencies(application)
    try:
        yield
    finally:
        close_graph_dependencies(application)
        logger.info("Shutting down %s.", settings.application_name)


def create_application(
    dataset_catalog_config: DatasetCatalogConfig | None = None,
) -> FastAPI:
    """Create and configure the Flood-Aware FastAPI application.

    Args:
        dataset_catalog_config: Explicit runtime dataset configuration when
            dataset-backed dependencies are required.
    """

    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.application_name,
        version=settings.version,
        debug=settings.debug,
        description="Flood decision-support backend for the Swat River Basin.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Muhammad Ilyas"},
        license_info={"name": "MIT"},
        lifespan=lifespan,
    )
    application.include_router(api_router, prefix=settings.api_prefix)
    if dataset_catalog_config is not None:
        configure_dataset_dependencies(application, dataset_catalog_config)
    application.add_exception_handler(HTTPException, handle_http_exception)
    application.add_exception_handler(
        RequestValidationError, handle_request_validation_error
    )
    application.add_exception_handler(ValidationException, handle_validation_exception)
    application.add_exception_handler(ApplicationError, handle_application_exception)
    application.add_exception_handler(
        DecisionGenerationError, handle_decision_generation_error
    )
    application.add_exception_handler(
        ConversationSessionNotFoundError, handle_conversation_session_not_found_error
    )
    application.add_exception_handler(Exception, handle_unexpected_exception)
    application.middleware("http")(log_request)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )
    return application


def run_application() -> None:
    """Run the application using host and port settings."""

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=str(settings.host),
        port=settings.port,
        log_level=settings.log_level.value.lower(),
    )


app = create_application()


if __name__ == "__main__":
    run_application()
