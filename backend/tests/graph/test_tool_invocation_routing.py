"""Verify deterministic graph tool invocation and single-tool degradation."""

import asyncio
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from backend.app.graph.graph import GraphBuilder
from backend.app.graph.nodes import ForecastNode, WeatherNode
from backend.app.graph.router import FloodSeverityRoutingPolicy
from backend.app.graph.runtime import GraphRuntime
from backend.app.graph.state import (
    Coordinate,
    GISEvidence,
    GraphState,
    NodeStatus,
    VillageEvidence,
    WeatherEvidence,
)
from backend.app.models.enums import FloodSeverity
from backend.tests.graph_test_support import forecast_result, state_factory


class _ToolSpyNode:
    """Represent one injected tool boundary while recording graph invocation."""

    def __init__(
        self,
        name: str,
        calls: list[str],
        update: Callable[[GraphState], GraphState] | None = None,
    ) -> None:
        """Initialize a deterministic tool spy and optional state projection."""
        self._name = name
        self._calls = calls
        self._update = update or (lambda state: state.model_copy())

    async def execute(self, state: GraphState) -> GraphState:
        """Record one tool invocation and return the isolated state update."""
        self._calls.append(self._name)
        return self._update(state)


class _PassiveNode:
    """Complete the graph without adding unrelated behavior to routing tests."""

    async def execute(self, state: GraphState) -> GraphState:
        """Return an immutable copy after completing the test-only step."""
        return state.model_copy()


class _CopyingEvidenceAggregator:
    """Complete aggregation without changing evidence in routing-focused tests."""

    async def aggregate(self, state: GraphState) -> GraphState:
        """Return an immutable copy to represent a completed aggregation step."""
        return state.model_copy()


def _runtime(
    severity: FloodSeverity,
    calls: list[str],
    *,
    weather_node: object | None = None,
    forecast_node: object | None = None,
    village_update: Callable[[GraphState], GraphState] | None = None,
) -> GraphRuntime:
    """Build a real runtime with deterministic tool-boundary spies."""
    classifier = Mock()
    classifier.classify.return_value = severity
    forecast = forecast_result()
    builder = GraphBuilder(
        weather_node=weather_node or _ToolSpyNode("weather", calls),
        forecast_node=forecast_node
        or _ToolSpyNode(
            "forecast",
            calls,
            lambda state: state.model_copy(update={"forecast_result": forecast}),
        ),
        gis_node=_ToolSpyNode(
            "gis",
            calls,
            lambda state: state.model_copy(
                update={"gis": GISEvidence(flood_zone=severity.value)}
            ),
        ),
        village_node=_ToolSpyNode("village", calls, village_update),
        shelter_node=_ToolSpyNode("shelter", calls),
        knowledge_node=_ToolSpyNode("knowledge", calls),
        dataset_node=_ToolSpyNode("dataset", calls),
        recommendation_node=_PassiveNode(),
        routing_policy=FloodSeverityRoutingPolicy(classifier),
        evidence_aggregator=_CopyingEvidenceAggregator(),
    )
    return GraphRuntime(graph_builder=builder)


def _state(request_text: str, village_name: str | None = None) -> GraphState:
    """Create a realistic immutable graph request for routing verification."""
    return state_factory().create(
        request_text=request_text,
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249),
        village_name=village_name,
        district="Swat",
        province="Khyber Pakhtunkhwa",
    )


async def _execute_concurrently(
    runtime: GraphRuntime, *states: GraphState
) -> tuple[GraphState, ...]:
    """Run independent graph states concurrently through one runtime instance."""
    return tuple(await asyncio.gather(*(runtime.execute(state) for state in states)))


# TODO(Sprint 13): Add approved query-intent routing once its policy is designed.
@pytest.mark.parametrize(
    "request_text,village_name",
    (
        ("What is the flood forecast for Swat?", None),
        ("How many people and assets may be affected?", "Mingora"),
        ("Which shelter should residents use?", "Mingora"),
        ("What does the PDMA policy require?", None),
        ("Give flood, population, shelter, and policy information.", "Mingora"),
    ),
)
def test_query_intent_does_not_change_current_normal_severity_tool_path(
    request_text: str, village_name: str | None
) -> None:
    """Current routing uses severity only, not the request's textual intent."""
    calls: list[str] = []
    runtime = _runtime(FloodSeverity.MINOR, calls)

    updated = asyncio.run(runtime.execute(_state(request_text, village_name)))

    assert calls == ["weather", "forecast", "knowledge", "dataset"]
    assert updated.runtime.completed_nodes == (
        "weather",
        "forecast",
        "knowledge",
        "dataset",
        "aggregate",
        "recommendation",
    )
    assert updated.runtime.skipped_nodes == ("gis", "village", "shelter")
    assert all(
        trace.status in {NodeStatus.COMPLETED, NodeStatus.SKIPPED}
        for trace in updated.execution_trace
    )


def test_weather_tool_failure_records_failed_trace_and_continues_graph() -> None:
    """One unavailable tool must leave partial evidence and complete the graph."""
    weather_tool = Mock()
    weather_tool.get_current_weather.side_effect = RuntimeError("weather unavailable")
    calls: list[str] = []
    runtime = _runtime(
        FloodSeverity.MINOR,
        calls,
        weather_node=WeatherNode(weather_tool),
    )

    updated = asyncio.run(runtime.execute(_state("What is the flood forecast?")))

    weather_tool.get_current_weather.assert_called_once()
    assert updated.weather == WeatherEvidence()
    assert updated.forecast_result is not None
    assert updated.errors[-1].source_node == "weather"
    assert updated.errors[-1].error_type == "RuntimeError"
    weather_trace = next(
        trace for trace in updated.execution_trace if trace.node_name == "weather"
    )
    assert weather_trace.status is NodeStatus.FAILED
    assert weather_trace.error == "weather unavailable"
    assert "weather" not in updated.runtime.skipped_nodes
    assert calls == ["forecast", "knowledge", "dataset"]


def test_coordinate_less_policy_request_skips_location_nodes_and_completes() -> None:
    """Expected input gaps are skipped while policy evidence still completes."""
    weather_tool = Mock()
    forecast_provider = Mock()
    calls: list[str] = []
    runtime = _runtime(
        FloodSeverity.MINOR,
        calls,
        weather_node=WeatherNode(weather_tool),
        forecast_node=ForecastNode(forecast_provider, Mock()),
    )
    state = state_factory().create(
        request_text="What does the PDMA preparedness policy require?"
    )

    updated = asyncio.run(runtime.execute(state))

    weather_tool.get_current_weather.assert_not_called()
    forecast_provider.get_forecast.assert_not_called()
    traces = {trace.node_name: trace for trace in updated.execution_trace}
    for node_name in ("weather", "forecast", "gis"):
        assert traces[node_name].status is NodeStatus.SKIPPED
        assert traces[node_name].skipped is True
    for node_name in ("knowledge", "dataset", "recommendation"):
        assert traces[node_name].status is NodeStatus.COMPLETED
    assert not updated.errors


def test_concurrent_runtime_execution_keeps_village_evidence_isolated() -> None:
    """Concurrent immutable states must not leak village evidence across requests."""
    calls: list[str] = []

    def village_update(state: GraphState) -> GraphState:
        return state.model_copy(
            update={
                "villages": (
                    VillageEvidence(village_name=state.user_request.village_name),
                )
            }
        )

    runtime = _runtime(FloodSeverity.MAJOR, calls, village_update=village_update)
    first = _state("Assess flood impacts for Mingora.", "Mingora")
    second = _state("Assess flood impacts for Saidu Sharif.", "Saidu Sharif")

    first_result, second_result = asyncio.run(
        _execute_concurrently(runtime, first, second)
    )

    assert first_result.villages[0].village_name == "Mingora"
    assert second_result.villages[0].village_name == "Saidu Sharif"
    assert first.villages == ()
    assert second.villages == ()
