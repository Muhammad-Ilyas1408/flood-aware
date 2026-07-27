"""LangGraph nodes with explicitly bounded orchestration responsibilities."""

import asyncio
import logging

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.decision.protocols import DecisionAgentProtocol
from backend.app.decision.exceptions import DecisionError
from backend.app.core.logger import get_logger
from backend.app.forecast.models import ForecastResult
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.models import PreparedFloodContext
from backend.app.gis.domain.protocols import ForecastProvider
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.graph.exceptions import (
    MissingCoordinatesError,
    MissingForecastResultError,
    MissingKnowledgeContextError,
    MissingWeatherCoordinatesError,
)
from backend.app.graph.mappers import (
    DatasetEvidenceMapper,
    DecisionFallbackMapper,
    DecisionRecommendationMapper,
    FloodEvidenceMapper,
    GraphCoordinateMapper,
    KnowledgeEvidenceMapper,
    ShelterEvidenceMapper,
    ToolContextMapper,
    VillageEvidenceMapper,
    WeatherEvidenceMapper,
    WeatherRequestMapper,
)
from backend.app.graph.state import GraphState
from backend.app.observability.context import ExecutionContext
from backend.app.observability.logging import log_event
from backend.app.observability.metrics import DecisionMetricsCollector
from backend.app.observability.timing import OperationTimer
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.weather.weather_tool import WeatherTool

_LOGGER = get_logger(__name__)


class WeatherNode:
    """Adapt graph coordinates to the production weather-tool boundary."""

    def __init__(self, weather_tool: WeatherTool) -> None:
        """Initialize the node with the injected production weather tool."""
        self._weather_tool = weather_tool

    async def execute(self, state: GraphState) -> GraphState:
        """Retrieve weather and update only graph-owned weather evidence."""
        coordinates = state.user_request.coordinates
        if coordinates is None:
            raise MissingWeatherCoordinatesError(
                "Weather retrieval requires request coordinates."
            )
        request = WeatherRequestMapper.to_domain(coordinates)
        result = await asyncio.to_thread(
            self._weather_tool.get_current_weather, request
        )
        return state.model_copy(
            update={"weather": WeatherEvidenceMapper.to_graph(result)}
        )


class ForecastNode:
    """Retain the canonical forecast result produced by an injected provider."""

    def __init__(self, forecast_provider: ForecastProvider) -> None:
        """Initialize the node with the injected production forecast boundary."""

        self._forecast_provider = forecast_provider

    async def execute(self, state: GraphState) -> GraphState:
        """Store the provider's canonical result without deriving new facts."""
        coordinates = state.user_request.coordinates
        if coordinates is None:
            raise MissingCoordinatesError("Forecast retrieval requires coordinates.")

        forecast_result = await asyncio.to_thread(
            self._forecast_provider.get_forecast,
            coordinates.latitude,
            coordinates.longitude,
        )
        if not isinstance(forecast_result, ForecastResult):
            raise TypeError("Forecast provider must return a ForecastResult.")

        return state.model_copy(update={"forecast_result": forecast_result})


class GISAnalysisNode:
    """Adapt prepared graph facts to the production GIS domain boundary."""

    def __init__(
        self,
        classification_service: FloodClassificationService,
        spatial_policy_service: SpatialPolicyService,
        gis_request_factory: GISRequestFactory,
        gis_domain_service: GISDomainService,
    ) -> None:
        """Initialize the node with its approved orchestration dependencies."""

        self._classification_service = classification_service
        self._spatial_policy_service = spatial_policy_service
        self._gis_request_factory = gis_request_factory
        self._gis_domain_service = gis_domain_service

    async def execute(self, state: GraphState) -> GraphState:
        """Execute the GIS domain service from canonical graph facts."""
        forecast = state.forecast_result
        if forecast is None:
            raise MissingForecastResultError(
                "GIS analysis requires a canonical ForecastResult."
            )
        graph_coordinates = state.user_request.coordinates
        if graph_coordinates is None:
            raise MissingCoordinatesError("GIS analysis requires request coordinates.")

        coordinates = GraphCoordinateMapper.to_domain(graph_coordinates)
        severity = self._classification_service.classify(forecast)
        bounds = self._spatial_policy_service.analysis_bounds(coordinates)
        request = self._gis_request_factory.build(
            PreparedFloodContext(
                forecast=forecast,
                severity=severity,
                bounds=bounds,
                coordinates=coordinates,
            )
        )
        evidence = await self._gis_domain_service.execute(request)
        return state.model_copy(update={"gis": FloodEvidenceMapper.to_graph(evidence)})


class DormantGISAnalysisNode:
    """Preserve the intentionally inactive GIS step in the foundation graph."""

    async def execute(self, state: GraphState) -> GraphState:
        """Return state unchanged until production dependencies are composed."""
        return state


class DormantGraphNode:
    """Preserve inactive graph steps when production dependencies are unavailable."""

    async def execute(self, state: GraphState) -> GraphState:
        """Return state unchanged for an intentionally dormant graph step."""
        return state


class VillageNode:
    """Adapt graph state to the production configured-village tool."""

    def __init__(self, village_tool: VillageTool) -> None:
        """Initialize the node with the injected production village tool."""
        self._village_tool = village_tool

    async def execute(self, state: GraphState) -> GraphState:
        """Retrieve villages and update only graph-owned village evidence."""
        context = ToolContextMapper.to_domain(state)
        result = await asyncio.to_thread(self._village_tool.execute, context)
        return state.model_copy(
            update={"villages": VillageEvidenceMapper.to_graph(result.data)}
        )


class ShelterNode:
    """Adapt graph state to the production configured-shelter tool."""

    def __init__(self, shelter_tool: ShelterTool) -> None:
        """Initialize the node with the injected production shelter tool."""
        self._shelter_tool = shelter_tool

    async def execute(self, state: GraphState) -> GraphState:
        """Retrieve shelters and update only graph-owned shelter evidence."""
        context = ToolContextMapper.to_domain(state)
        result = await asyncio.to_thread(self._shelter_tool.execute, context)
        return state.model_copy(
            update={"shelters": ShelterEvidenceMapper.to_graph(result.data)}
        )


class DatasetCatalogNode:
    """Adapt graph state to the production dataset-catalog tool."""

    def __init__(self, dataset_catalog_tool: DatasetCatalogTool) -> None:
        """Initialize the node with the injected production catalog tool."""
        self._dataset_catalog_tool = dataset_catalog_tool

    async def execute(self, state: GraphState) -> GraphState:
        """Retrieve catalog metadata and update only dataset graph evidence."""
        context = ToolContextMapper.to_domain(state)
        result = await asyncio.to_thread(self._dataset_catalog_tool.execute, context)
        return state.model_copy(
            update={"datasets": DatasetEvidenceMapper.to_graph(result.data)}
        )


class GovernmentKnowledgeNode:
    """Adapt the graph question to the production government-knowledge tool."""

    def __init__(self, knowledge_tool: KnowledgeTool) -> None:
        """Initialize the node with the injected production knowledge tool."""
        self._knowledge_tool = knowledge_tool

    async def execute(self, state: GraphState) -> GraphState:
        """Retrieve grounded knowledge and update only knowledge evidence."""
        question = state.user_request.request_text
        if not question.strip():
            raise MissingKnowledgeContextError(
                "Government knowledge retrieval requires a user question."
            )
        answer = await asyncio.to_thread(self._knowledge_tool.answer, question)
        return state.model_copy(
            update={"knowledge": KnowledgeEvidenceMapper.to_graph(answer)}
        )


class RecommendationNode:
    """Orchestrate the injected decision agent from canonical aggregated evidence.

    This node never reasons, parses, builds prompts, or communicates with OpenAI.
    It delegates those responsibilities to the injected ``DecisionAgentProtocol``
    and maps the resulting validated decision into its owned graph-state section.
    """

    def __init__(
        self,
        decision_agent: DecisionAgentProtocol,
        metrics: DecisionMetricsCollector | None = None,
    ) -> None:
        """Initialize the node with the injected evidence-only decision agent."""
        self._decision_agent = decision_agent
        self._metrics = metrics

    async def execute(self, state: GraphState) -> GraphState:
        """Update only recommendation evidence from the canonical bundle."""
        timer = OperationTimer.start()
        context = ExecutionContext.from_graph_state(state)
        try:
            decision = await self._decision_agent.decide(
                state.evidence_bundle,
                execution_context=context,
            )
        except DecisionError as error:
            if self._metrics is not None:
                self._metrics.record_fallback(context)
            log_event(
                _LOGGER,
                logging.WARNING,
                "decision_generation_fallback_used",
                context,
                node="recommendation",
                duration_ms=timer.elapsed_ms(),
                retry_count=0,
                timeout=False,
                fallback_used=True,
                failure_type=type(error).__name__,
            )
            mapper_timer = OperationTimer.start()
            fallback = DecisionFallbackMapper.unavailable()
            log_event(
                _LOGGER,
                logging.INFO,
                "decision_fallback_mapper_finished",
                context,
                node="recommendation",
                duration_ms=mapper_timer.elapsed_ms(),
            )
            return state.model_copy(update={"recommendation": fallback})
        mapper_timer = OperationTimer.start()
        recommendation = DecisionRecommendationMapper.to_graph(decision)
        log_event(
            _LOGGER,
            logging.INFO,
            "decision_mapper_finished",
            context,
            node="recommendation",
            duration_ms=mapper_timer.elapsed_ms(),
            risk_level=recommendation.risk_level,
        )
        return state.model_copy(update={"recommendation": recommendation})
