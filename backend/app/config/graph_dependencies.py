"""Application composition root for the production graph and conversation stack.

This module constructs the full LangGraph decision pipeline exactly as
``scripts/manual_chat.py``'s ``_build_container`` does, but once at FastAPI
startup instead of once per script run, so expensive GIS resources (river
network and OSM PBF parsing) are read once and reused across every request.

Weather and forecast now use their real production boundaries. Weather calls
OpenWeatherMap synchronously per request. Forecast reads the newest already-
ingested local GloFAS snapshot from ``data/glofas/`` only; it never triggers
live GloFAS/CDS ingestion, which remains a separate, independently-run
process (``scripts/ingest_glofas_snapshot.py``) explicitly out of scope here.
"""

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.config.datasets import create_production_dataset_catalog_config
from backend.app.config.settings import PROJECT_ROOT, get_settings
from backend.app.conversation import ConversationOrchestrator, ConversationSessionStore
from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.decision.dependencies import build_openai_decision_provider
from backend.app.decision.prompt_builder import PromptBuilder as DecisionPromptBuilder
from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.forecast.constants import DEFAULT_SNAPSHOT_DIRECTORY
from backend.app.forecast.forecast_tool import GloFASForecastTool
from backend.app.forecast.mapper import ForecastMapper
from backend.app.forecast.parser import NetCDFForecastParser
from backend.app.forecast.settings import ForecastSettings
from backend.app.forecast.snapshot_locator import SnapshotLocator
from backend.app.gis.analysis_tool import GISAnalysisTool
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.models import SpatialPolicy
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.gis.evidence import FloodEvidenceBuilder
from backend.app.gis.processing.flood_zone import FloodZoneGenerator
from backend.app.gis.processing.infrastructure_impact import InfrastructureImpactCalculator
from backend.app.gis.processing.osm import OSMLoader
from backend.app.gis.processing.population_exposure import PopulationExposureCalculator
from backend.app.gis.processing.worldpop import WorldPopLoader
from backend.app.gis.river.loader import RiverNetworkLoader
from backend.app.graph.container import GraphContainer, GraphDependencies
from backend.app.graph.factory import GraphStateFactory
from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.embedding_service import OpenAIEmbeddingService
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.prompt_builder import PromptBuilder as RAGPromptBuilder
from backend.app.rag.response_generator import OpenAIResponseGenerator
from backend.app.rag.retriever import GovernmentRetriever
from backend.app.rag.settings import GovernmentKnowledgeSettings
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.services.dependencies import (
    create_dataset_catalog_service,
    create_shelter_service,
    create_village_service,
)
from backend.app.use_cases.dataset_catalog import ViewDatasetCatalogUseCase
from backend.app.use_cases.shelters import ViewSheltersUseCase
from backend.app.use_cases.villages import ViewVillagesUseCase
from backend.app.weather.client import OpenWeatherClient
from backend.app.weather.settings import WeatherSettings
from backend.app.weather.weather_tool import WeatherTool

_OSM_PBF_PATH = PROJECT_ROOT / "data/gis/osm/raw/pakistan-latest.osm.pbf"
_WORLDPOP_RASTER_PATH = PROJECT_ROOT / "data/gis/worldpop/raw/pak_ppp_2025.tif"


@dataclass(frozen=True, slots=True)
class _GraphRuntimeResources:
    """Own closable GIS/RAG/weather resources constructed once for the app's lifetime."""

    vector_store: ChromaVectorStore
    river_loader: RiverNetworkLoader
    worldpop_loader: WorldPopLoader
    weather_client: OpenWeatherClient

    def close(self) -> None:
        """Release every owned resource at application shutdown."""
        self.vector_store.close()
        self.river_loader.close()
        self.worldpop_loader.close()
        self.weather_client.close()


def _build_knowledge_tool() -> tuple[KnowledgeTool, ChromaVectorStore]:
    """Compose the production government-knowledge retrieval boundary.

    Raises:
        ApplicationConfigurationError: If ``OPENAI_API_KEY`` is unavailable.
    """
    settings = GovernmentKnowledgeSettings()
    if not settings.openai_api_key:
        raise ApplicationConfigurationError(
            "OPENAI_API_KEY is required to build the government knowledge tool."
        )
    store = ChromaVectorStore(settings.chroma_directory, settings.collection_name)
    retriever = GovernmentRetriever(
        OpenAIEmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        ),
        store,
    )
    return (
        KnowledgeTool(
            retriever,
            ContextBuilder(settings.context_max_characters),
            RAGPromptBuilder(),
            OpenAIResponseGenerator(
                api_key=settings.openai_api_key,
                model=settings.response_model,
            ),
        ),
        store,
    )


def _build_weather_tool(
    settings: WeatherSettings,
) -> tuple[WeatherTool, OpenWeatherClient]:
    """Compose the production OpenWeatherMap-backed Weather Tool.

    The owned HTTP client is returned alongside the tool so its lifetime can
    be closed explicitly at application shutdown.

    Raises:
        ApplicationConfigurationError: If ``OPENWEATHER_API_KEY`` is unavailable.
    """
    if not settings.openweather_api_key:
        raise ApplicationConfigurationError(
            "OPENWEATHER_API_KEY is required to build the production weather tool."
        )
    client = OpenWeatherClient(settings)
    return WeatherTool(client), client


def _build_forecast_provider(settings: ForecastSettings) -> GloFASForecastTool:
    """Compose the production forecast tool reading the local snapshot directory only.

    This never triggers live GloFAS/CDS ingestion: it only parses whatever
    snapshot ``scripts/ingest_glofas_snapshot.py`` has already saved locally.
    """
    return GloFASForecastTool(
        parser=NetCDFForecastParser(),
        mapper=ForecastMapper(),
        snapshot_locator=SnapshotLocator(DEFAULT_SNAPSHOT_DIRECTORY),
    )


def _require_existing_file(path: Path, description: str) -> None:
    """Fail fast when a required production data file is missing."""
    if not path.is_file():
        raise ApplicationConfigurationError(
            f"Required {description} is missing at {path}."
        )


def configure_graph_dependencies(application: FastAPI) -> None:
    """Construct the production graph and conversation stack once at startup.

    Builds every real collaborator the graph needs (the OpenWeatherMap-backed
    weather tool, the local-snapshot GloFAS forecast tool, village/shelter/
    dataset services and tools, GIS river/OSM/worldpop loaders and domain
    service, the government-knowledge tool, and the real OpenAI decision
    provider), then wires one ``GraphContainer`` and one
    ``ConversationOrchestrator`` and attaches them to ``application.state``
    so they persist for the application's lifetime and are reused across
    every request.

    Args:
        application: The FastAPI application that owns the runtime state.

    Raises:
        ApplicationConfigurationError: If required data files or the OpenAI
            or OpenWeatherMap API keys are missing.
    """
    _require_existing_file(_OSM_PBF_PATH, "OSM PBF dataset")
    _require_existing_file(_WORLDPOP_RASTER_PATH, "WorldPop raster dataset")

    weather_tool, weather_client = _build_weather_tool(WeatherSettings())
    forecast_settings = ForecastSettings()
    forecast_provider = _build_forecast_provider(forecast_settings)

    dataset_config = create_production_dataset_catalog_config()
    village_service = create_village_service(
        dataset_config.villages.dataset_path,
        dataset_config.villages.dataset_metadata,
        dataset_config.villages.dataset_schema,
    )
    shelter_service = create_shelter_service(
        dataset_config.shelters.dataset_path,
        dataset_config.shelters.dataset_metadata,
        dataset_config.shelters.dataset_schema,
    )
    knowledge_tool, vector_store = _build_knowledge_tool()

    worldpop_loader = WorldPopLoader(_WORLDPOP_RASTER_PATH)
    river_loader = RiverNetworkLoader(_OSM_PBF_PATH)
    gis_domain_service = GISDomainService(
        river_loader=river_loader,
        osm_loader=OSMLoader(_OSM_PBF_PATH),
        gis_analysis_tool=GISAnalysisTool(
            FloodZoneGenerator(),
            PopulationExposureCalculator(worldpop_loader),
            InfrastructureImpactCalculator(),
            FloodEvidenceBuilder(),
        ),
    )
    classification_service = FloodClassificationService(
        FloodClassificationPolicy.from_settings(get_settings())
    )
    decision_agent = build_openai_decision_provider()
    dependencies = GraphDependencies(
        weather_tool=weather_tool,
        forecast_provider=forecast_provider,
        flood_classification_service=classification_service,
        spatial_policy_service=SpatialPolicyService(SpatialPolicy()),
        gis_request_factory=GISRequestFactory(),
        gis_domain_service=gis_domain_service,
        village_tool=VillageTool(ViewVillagesUseCase(village_service)),
        shelter_tool=ShelterTool(ViewSheltersUseCase(shelter_service)),
        dataset_catalog_tool=DatasetCatalogTool(
            ViewDatasetCatalogUseCase(create_dataset_catalog_service(dataset_config))
        ),
        knowledge_tool=knowledge_tool,
        decision_agent=decision_agent,
        forecast_max_snapshot_age_hours=forecast_settings.glofas_max_snapshot_age_hours,
    )
    container = GraphContainer(dependencies)
    orchestrator = ConversationOrchestrator(
        graph_runtime=container.graph_runtime,
        decision_agent=decision_agent,
        prompt_builder=DecisionPromptBuilder(),
        session_store=ConversationSessionStore(),
        state_factory=GraphStateFactory(),
    )

    application.state.graph_container = container
    application.state.conversation_orchestrator = orchestrator
    application.state.graph_runtime_resources = _GraphRuntimeResources(
        vector_store=vector_store,
        river_loader=river_loader,
        worldpop_loader=worldpop_loader,
        weather_client=weather_client,
    )


def close_graph_dependencies(application: FastAPI) -> None:
    """Release resources constructed by ``configure_graph_dependencies``, if any."""
    resources = getattr(application.state, "graph_runtime_resources", None)
    if isinstance(resources, _GraphRuntimeResources):
        resources.close()


def get_conversation_orchestrator(request: Request) -> ConversationOrchestrator:
    """Provide the singleton conversation orchestrator configured at startup."""
    orchestrator = getattr(request.app.state, "conversation_orchestrator", None)
    if not isinstance(orchestrator, ConversationOrchestrator):
        raise ApplicationConfigurationError(
            "Application graph dependencies require a configured "
            "ConversationOrchestrator."
        )
    return orchestrator
