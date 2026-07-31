"""Interact manually with the Flood-Aware graph before the Streamlit UI exists.

This development-only script is not part of the production application or test
suite.  It uses local GIS and dataset resources, deterministic weather and
forecast stand-ins, and makes real OpenAI calls for both government-knowledge
retrieval and decision generation.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config.logging import configure_logging
from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.config.datasets import create_production_dataset_catalog_config
from backend.app.config.logging import configure_logging
from backend.app.config.settings import get_settings
from backend.app.conversation import ConversationOrchestrator, ConversationSessionStore
from backend.app.decision.agent import OpenAIDecisionProvider
from backend.app.decision.dependencies import build_openai_decision_provider
from backend.app.decision.models import Decision
from backend.app.decision.prompt_builder import PromptBuilder as DecisionPromptBuilder
from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.flood.classification.service import FloodClassificationService
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
from backend.app.graph.state import Coordinate, UserRequest
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
_MINGORA_COORDINATES = Coordinate(latitude=34.7700, longitude=72.3600)


class _StaticWeatherTool:
    """Provide the existing graph-test weather fixture without network I/O."""

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
            source="manual_chat_static_weather",
        )


class _StaticForecastProvider:
    """Provide the existing graph-test forecast fixture without GloFAS I/O."""

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


def _build_knowledge_tool() -> tuple[KnowledgeTool, ChromaVectorStore]:
    """Compose the existing production government-knowledge retrieval boundary."""
    settings = GovernmentKnowledgeSettings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for manual chat.")
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
            score_threshold=settings.retrieval_score_threshold,
        ),
        store,
    )


def _build_container() -> tuple[
    GraphContainer,
    ChromaVectorStore,
    RiverNetworkLoader,
    WorldPopLoader,
    OpenAIDecisionProvider,
]:
    """Compose the production graph with local resources and safe API stand-ins."""
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

    osm_path = PROJECT_ROOT / "data/gis/osm/raw/swat-region.osm.pbf"
    worldpop_loader = WorldPopLoader(
        PROJECT_ROOT / "data/gis/worldpop/raw/swat-region_ppp_2025.tif"
    )
    river_loader = RiverNetworkLoader(osm_path)
    gis_domain_service = GISDomainService(
        river_loader=river_loader,
        osm_loader=OSMLoader(osm_path),
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
    return (
        GraphContainer(dependencies),
        vector_store,
        river_loader,
        worldpop_loader,
        decision_agent,
    )


def _print_decision(decision: Decision) -> None:
    """Render the stable public decision fields for a terminal conversation."""
    recommendation = decision.recommendation
    print(f"\nRisk: {decision.risk_assessment.level.value}")
    print(f"Confidence: {decision.confidence.value}")
    print(f"Summary: {recommendation.summary}")
    if recommendation.actions:
        print("Actions:")
        for action in recommendation.actions:
            print(f"  - [{action.priority.value}] {action.action}")
    if recommendation.citations:
        print("Citations:")
        for citation in recommendation.citations:
            print(f"  - {citation}")
    print()


async def main() -> None:
    """Run a terminal conversation using one reusable Flood-Aware session."""
    configure_logging(get_settings().log_level)
    village_name = input("Village [Mingora]: ").strip() or "Mingora"
    (
        container,
        vector_store,
        river_loader,
        worldpop_loader,
        decision_agent,
    ) = _build_container()
    orchestrator = ConversationOrchestrator(
        graph_runtime=container.graph_runtime,
        decision_agent=decision_agent,
        prompt_builder=DecisionPromptBuilder(),
        session_store=ConversationSessionStore(),
        state_factory=GraphStateFactory(),
    )
    session_id = None
    print("Flood-Aware manual chat. Type 'exit' to quit.")
    try:
        while True:
            question = input("You: ").strip()
            if question.lower() == "exit":
                return
            if not question:
                continue
            request = UserRequest(
                request_text=question,
                coordinates=_MINGORA_COORDINATES,
                village_name=village_name,
                district="Swat",
                province="Khyber Pakhtunkhwa",
            )
            session_id, decision = await orchestrator.handle_turn(session_id, request)
            _print_decision(decision)
    finally:
        vector_store.close()
        river_loader.close()
        worldpop_loader.close()

if __name__ == "__main__":
    asyncio.run(main())
