"""Build the deterministic conditional LangGraph evidence workflow."""

from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from backend.app.graph.contracts import (
    EvidenceAggregatorProtocol,
    GraphNodeProtocol,
    RouterProtocol,
)
from backend.app.graph.state import GraphState

GraphStep = Callable[[GraphState], Awaitable[GraphState]]
TraceWrapper = Callable[[str, GraphStep], GraphStep]


class GraphBuilder:
    """Build the deterministic, reasoning-free evidence collection workflow.

    The graph uses injected routing only to skip unnecessary analysis from
    immutable state. It remains independent of concrete node implementations,
    and recommendation reasoning is not registered in this workflow.
    """

    def __init__(
        self,
        *,
        weather_node: GraphNodeProtocol,
        forecast_node: GraphNodeProtocol,
        gis_node: GraphNodeProtocol,
        village_node: GraphNodeProtocol,
        shelter_node: GraphNodeProtocol,
        knowledge_node: GraphNodeProtocol,
        dataset_node: GraphNodeProtocol,
        recommendation_node: GraphNodeProtocol,
        routing_policy: RouterProtocol,
        evidence_aggregator: EvidenceAggregatorProtocol,
    ) -> None:
        """Initialize one graph from injected nodes and deterministic routing."""
        self._nodes: tuple[tuple[str, GraphNodeProtocol], ...] = (
            ("weather", weather_node),
            ("forecast", forecast_node),
            ("gis", gis_node),
            ("village", village_node),
            ("shelter", shelter_node),
            ("knowledge", knowledge_node),
            ("dataset", dataset_node),
            ("recommendation", recommendation_node),
        )
        self._routing_policy = routing_policy
        self._evidence_aggregator = evidence_aggregator

    @property
    def step_names(self) -> tuple[str, ...]:
        """Return stable graph-step names for runtime trace finalization."""
        return tuple(name for name, _ in self._nodes) + ("aggregate",)

    def compile(self, *, trace_wrapper: TraceWrapper | None = None):
        """Compile deterministic evidence collection with conditional edges.

        Nodes remain implementation-agnostic inputs. The injected routing policy
        selects only the next graph edge from immutable state; it never executes
        tools or changes state. Recommendation reasoning remains out of scope.
        """
        graph = StateGraph(GraphState)
        for name, node in self._nodes:
            graph.add_node(name, _trace_step(name, node.execute, trace_wrapper))
        graph.add_node(
            "aggregate",
            _trace_step(
                "aggregate", self._evidence_aggregator.aggregate, trace_wrapper
            ),
        )
        graph.add_edge(START, self._nodes[0][0])
        graph.add_edge("weather", "forecast")
        graph.add_conditional_edges(
            "forecast",
            self._routing_policy.route_after_forecast,
            {"gis": "gis", "knowledge": "knowledge"},
        )
        graph.add_conditional_edges(
            "gis",
            self._routing_policy.route_after_gis,
            {"village": "village", "knowledge": "knowledge"},
        )
        graph.add_edge("village", "shelter")
        graph.add_edge("shelter", "knowledge")
        graph.add_edge("knowledge", "dataset")
        graph.add_edge("dataset", "aggregate")
        graph.add_edge("aggregate", "recommendation")
        graph.add_edge("recommendation", END)
        return graph.compile()


def _trace_step(
    name: str,
    step: GraphStep,
    trace_wrapper: TraceWrapper | None,
) -> GraphStep:
    """Apply optional runtime-owned execution instrumentation to one step."""
    return trace_wrapper(name, step) if trace_wrapper is not None else step
