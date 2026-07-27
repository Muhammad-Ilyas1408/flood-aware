"""Composition root for the isolated LangGraph infrastructure."""

from dataclasses import dataclass

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.decision.protocols import DecisionAgentProtocol
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.protocols import ForecastProvider
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.graph.adapters.runtime_adapter import RuntimeAdapter, RuntimeSelection
from backend.app.graph.aggregator import EvidenceAggregator
from backend.app.graph.contracts import SequentialRuntimeProtocol
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.graph import GraphBuilder
from backend.app.graph.mapper import DecisionContextMapper
from backend.app.graph.nodes import (
    DatasetCatalogNode,
    ForecastNode,
    GISAnalysisNode,
    GovernmentKnowledgeNode,
    RecommendationNode,
    ShelterNode,
    VillageNode,
    WeatherNode,
)
from backend.app.graph.router import FloodSeverityRoutingPolicy
from backend.app.graph.runtime import GraphRuntime
from backend.app.observability.metrics import (
    DecisionMetricsCollector,
    LoggingDecisionMetricsCollector,
)
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.weather.weather_tool import WeatherTool


@dataclass(frozen=True, slots=True)
class GraphDependencies:
    """Collect the explicit production boundaries required by the graph.

    The application composition layer constructs these existing boundaries.
    ``GraphContainer`` owns their graph-node wiring without duplicating their
    subsystem-specific construction.
    """

    weather_tool: WeatherTool
    forecast_provider: ForecastProvider
    flood_classification_service: FloodClassificationService
    spatial_policy_service: SpatialPolicyService
    gis_request_factory: GISRequestFactory
    gis_domain_service: GISDomainService
    village_tool: VillageTool
    shelter_tool: ShelterTool
    dataset_catalog_tool: DatasetCatalogTool
    knowledge_tool: KnowledgeTool
    decision_agent: DecisionAgentProtocol
    decision_metrics: DecisionMetricsCollector | None = None


class GraphContainer:
    """Assemble graph collaborators through explicit, lightweight composition."""

    def __init__(
        self,
        dependencies: GraphDependencies,
    ) -> None:
        """Construct the fully wired production graph from injected boundaries."""
        self._state_factory = GraphStateFactory()
        self._context_mapper = DecisionContextMapper(self._state_factory)
        decision_metrics = (
            dependencies.decision_metrics or LoggingDecisionMetricsCollector()
        )
        self._graph_builder = GraphBuilder(
            weather_node=WeatherNode(dependencies.weather_tool),
            forecast_node=ForecastNode(dependencies.forecast_provider),
            gis_node=GISAnalysisNode(
                dependencies.flood_classification_service,
                dependencies.spatial_policy_service,
                dependencies.gis_request_factory,
                dependencies.gis_domain_service,
            ),
            village_node=VillageNode(dependencies.village_tool),
            shelter_node=ShelterNode(dependencies.shelter_tool),
            knowledge_node=GovernmentKnowledgeNode(dependencies.knowledge_tool),
            dataset_node=DatasetCatalogNode(dependencies.dataset_catalog_tool),
            recommendation_node=RecommendationNode(
                dependencies.decision_agent,
                metrics=decision_metrics,
            ),
            routing_policy=FloodSeverityRoutingPolicy(
                dependencies.flood_classification_service
            ),
            evidence_aggregator=EvidenceAggregator(),
        )
        self._graph_runtime = GraphRuntime(graph_builder=self._graph_builder)

    @property
    def graph_runtime(self) -> GraphRuntime:
        """Return the isolated graph runtime owned by this composition root."""
        return self._graph_runtime

    @property
    def context_mapper(self) -> DecisionContextMapper:
        """Return the canonical DecisionContext-to-GraphState mapper."""
        return self._context_mapper

    def create_runtime_adapter(
        self,
        sequential_runtime: SequentialRuntimeProtocol,
        *,
        selection: RuntimeSelection = RuntimeSelection.SEQUENTIAL,
    ) -> RuntimeAdapter:
        """Create an adapter while preserving sequential runtime as the default."""
        return RuntimeAdapter(
            sequential_runtime=sequential_runtime,
            graph_runtime=self._graph_runtime,
            context_mapper=self._context_mapper,
            selection=selection,
        )
