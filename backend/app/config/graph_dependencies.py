"""Application composition root for the production graph and conversation stack.

This module constructs the full LangGraph decision pipeline exactly as
``scripts/manual_chat.py``'s ``_build_container`` does, but once at FastAPI
startup instead of once per script run, so expensive GIS resources (river
network and OSM PBF parsing) are read once and reused across every request.

Weather and forecast evidence intentionally use the same deterministic
stand-ins as ``manual_chat.py`` rather than live provider integrations;
wiring the real ``WeatherTool``/GloFAS forecast provider into this graph is
explicitly out of scope for this composition root.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
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
from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.gis.analysis_tool import GISAnalysisTool
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.models import SpatialPolicy
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.gis.evidence import FloodEvidenceBuilder
from backend.app.gis.geometry import DistanceResult, Point
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
from backend.app.weather.models import WeatherRequest, WeatherResult

_FIXTURE_TIMESTAMP = datetime(2026, 7, 26, tzinfo=UTC)
_OSM_PBF_PATH = PROJECT_ROOT / "data/gis/osm/raw/pakistan-latest.osm.pbf"
_WORLDPOP_RASTER_PATH = PROJECT_ROOT / "data/gis/worldpop/raw/pak_ppp_2025.tif"


class _StaticWeatherTool:
    """Provide deterministic weather evidence pending live weather integration."""

    def get_current_weather(self, request: WeatherRequest) -> WeatherResult:
        """Return deterministic, realistic weather for the requested coordinates."""
        return WeatherResult(
            location="Mingora",
            country="PK",
            latitude=request.latitude,
            longitude=request.longitude,
            temperature=22.5,
            feels_like=22.5,
            humidity=80,
            pressure=1012,
            wind_speed=3.0,
            weather_condition="Rain",
            weather_description="light rain",
            rainfall=1.2,
            timestamp=_FIXTURE_TIMESTAMP,
            source="graph_dependencies_static_weather",
        )


class _StaticForecastProvider:
    """Provide deterministic forecast evidence pending live GloFAS integration."""

    def get_forecast(self, latitude: float, longitude: float) -> ForecastResult:
        """Return a deterministic major-discharge forecast at the requested point."""
        point = Point(latitude=latitude, longitude=longitude)
        return ForecastResult(
            location=ForecastLocation(
                requested_point=point,
                grid_point=point,
                grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
            ),
            metadata=ForecastMetadata(
                snapshot_path=PROJECT_ROOT
                / "data/glofas/glofas_control_20260726T000000Z.nc",
                dataset_name="cems-glofas-forecast",
                product_type="control_forecast",
                hydrological_model="lisflood",
                system_version="operational",
                forecast_reference_time=_FIXTURE_TIMESTAMP,
                retrieved_at=_FIXTURE_TIMESTAMP,
            ),
            series=ForecastSeries(
                points=(
                    ForecastPoint(
                        valid_time=_FIXTURE_TIMESTAMP,
                        lead_time_hours=0,
                        discharge_m3_per_second=600.0,
                    ),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class _GraphRuntimeResources:
    """Own closable GIS/RAG resources constructed once for the app's lifetime."""

    vector_store: ChromaVectorStore
    river_loader: RiverNetworkLoader
    worldpop_loader: WorldPopLoader

    def close(self) -> None:
        """Release every owned resource at application shutdown."""
        self.vector_store.close()
        self.river_loader.close()
        self.worldpop_loader.close()


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


def _require_existing_file(path: Path, description: str) -> None:
    """Fail fast when a required production data file is missing."""
    if not path.is_file():
        raise ApplicationConfigurationError(
            f"Required {description} is missing at {path}."
        )


def configure_graph_dependencies(application: FastAPI) -> None:
    """Construct the production graph and conversation stack once at startup.

    Builds every real collaborator the graph needs (village/shelter/dataset
    services and tools, GIS river/OSM/worldpop loaders and domain service,
    the government-knowledge tool, and the real OpenAI decision provider),
    then wires one ``GraphContainer`` and one ``ConversationOrchestrator``
    and attaches them to ``application.state`` so they persist for the
    application's lifetime and are reused across every request.

    Args:
        application: The FastAPI application that owns the runtime state.

    Raises:
        ApplicationConfigurationError: If required data files or the OpenAI
            API key are missing.
    """
    _require_existing_file(_OSM_PBF_PATH, "OSM PBF dataset")
    _require_existing_file(_WORLDPOP_RASTER_PATH, "WorldPop raster dataset")

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
        weather_tool=_StaticWeatherTool(),
        forecast_provider=_StaticForecastProvider(),
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
