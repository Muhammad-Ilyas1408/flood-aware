"""Shared deterministic fixtures for focused LangGraph tests."""

from datetime import UTC, datetime
from uuid import UUID

from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.gis.geometry import DistanceResult, Point
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.graph import GraphBuilder
from backend.app.graph.nodes import DormantGISAnalysisNode, DormantGraphNode
from backend.app.graph.state import GraphState


class FixedUuidFactory:
    """Provide deterministic identifiers for graph-state test setup."""

    def __init__(self) -> None:
        self._values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            )
        )

    def __call__(self) -> UUID:
        """Return the next predetermined UUID."""
        return next(self._values)


def state_factory() -> GraphStateFactory:
    """Create a graph-state factory with deterministic identifiers and time."""
    return GraphStateFactory(
        uuid_factory=FixedUuidFactory(),
        clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
    )


def forecast_result(
    *,
    discharge_m3_per_second: float = 100.0,
    retrieved_at: datetime | None = None,
) -> ForecastResult:
    """Create complete canonical forecast data without external I/O."""
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    requested_point = Point(latitude=34.0151, longitude=71.5249)
    return ForecastResult(
        location=ForecastLocation(
            requested_point=requested_point,
            grid_point=requested_point,
            grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
        ),
        metadata=ForecastMetadata(
            snapshot_path="data/glofas/glofas_control_20260726T000000Z.nc",
            dataset_name="cems-glofas-forecast",
            product_type="control_forecast",
            hydrological_model="lisflood",
            system_version="operational",
            forecast_reference_time=timestamp,
            retrieved_at=retrieved_at or timestamp,
        ),
        series=ForecastSeries(
            points=(
                ForecastPoint(
                    valid_time=timestamp,
                    lead_time_hours=0,
                    discharge_m3_per_second=discharge_m3_per_second,
                ),
            )
        ),
    )


def dormant_graph_builder() -> GraphBuilder:
    """Assemble explicit no-op nodes for isolated graph-runtime tests."""
    return GraphBuilder(
        weather_node=DormantGraphNode(),
        forecast_node=DormantGraphNode(),
        gis_node=DormantGISAnalysisNode(),
        village_node=DormantGraphNode(),
        shelter_node=DormantGraphNode(),
        knowledge_node=DormantGraphNode(),
        dataset_node=DormantGraphNode(),
        recommendation_node=DormantGraphNode(),
        routing_policy=NoOpRoutingPolicy(),
        evidence_aggregator=NoOpEvidenceAggregator(),
    )


class NoOpRoutingPolicy:
    """Route isolated runtime tests through the non-GIS evidence path."""

    def route_after_forecast(self, state: object) -> str:
        """Skip unavailable forecast-dependent processing in no-op tests."""
        del state
        return "knowledge"

    def route_after_gis(self, state: object) -> str:
        """Skip community analysis in no-op tests."""
        del state
        return "knowledge"


class NoOpEvidenceAggregator:
    """Keep runtime tests focused on execution rather than aggregation facts."""

    async def aggregate(self, state: GraphState) -> GraphState:
        """Return state unchanged for isolated runtime behavior tests."""
        return state
