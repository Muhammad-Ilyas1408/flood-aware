"""Focused tests for deterministic conditional graph routing."""

import asyncio
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from backend.app.graph.graph import GraphBuilder
from backend.app.graph.router import FloodSeverityRoutingPolicy
from backend.app.graph.runtime import GraphRuntime
from backend.app.graph.state import GISEvidence, GraphState
from backend.app.models.enums import FloodSeverity
from backend.tests.graph_test_support import (
    NoOpEvidenceAggregator,
    forecast_result,
    state_factory,
)


class RecordingNode:
    """Record graph execution while returning a new immutable state if needed."""

    def __init__(
        self,
        name: str,
        calls: list[str],
        update: Callable[[GraphState], GraphState] | None = None,
    ) -> None:
        """Initialize deterministic test-only node behavior."""
        self._name = name
        self._calls = calls
        self._update = update or (lambda state: state)

    async def execute(self, state: GraphState) -> GraphState:
        """Record this node and return only its supplied immutable update."""
        self._calls.append(self._name)
        return self._update(state)


def _execute_path(severity: FloodSeverity) -> tuple[list[str], GraphState, GraphState]:
    """Execute a graph that records the path selected for one severity."""
    calls: list[str] = []
    classifier = Mock()
    classifier.classify.return_value = severity
    forecast = forecast_result()
    builder = GraphBuilder(
        weather_node=RecordingNode("weather", calls),
        forecast_node=RecordingNode(
            "forecast",
            calls,
            lambda state: state.model_copy(update={"forecast_result": forecast}),
        ),
        gis_node=RecordingNode(
            "gis",
            calls,
            lambda state: state.model_copy(
                update={"gis": GISEvidence(flood_zone=severity.value)}
            ),
        ),
        village_node=RecordingNode("village", calls),
        shelter_node=RecordingNode("shelter", calls),
        knowledge_node=RecordingNode("knowledge", calls),
        dataset_node=RecordingNode("dataset", calls),
        recommendation_node=RecordingNode("recommendation", calls),
        routing_policy=FloodSeverityRoutingPolicy(classifier),
        evidence_aggregator=NoOpEvidenceAggregator(),
    )
    state = state_factory().create()
    updated = asyncio.run(GraphRuntime(graph_builder=builder).execute(state))
    classifier.classify.assert_called_once_with(forecast)
    return calls, state, updated


def test_minor_forecast_skips_gis_and_continues_to_knowledge() -> None:
    """Normal operational conditions should avoid unnecessary GIS execution."""
    calls, state, updated = _execute_path(FloodSeverity.MINOR)

    assert calls == ["weather", "forecast", "knowledge", "dataset", "recommendation"]
    assert state.forecast_result is None
    assert updated.forecast_result is not None


def test_moderate_forecast_executes_gis_without_community_analysis() -> None:
    """Moderate severity should collect GIS evidence but skip village and shelter."""
    calls, _, _ = _execute_path(FloodSeverity.MODERATE)

    assert calls == [
        "weather",
        "forecast",
        "gis",
        "knowledge",
        "dataset",
        "recommendation",
    ]


def test_major_forecast_executes_village_and_shelter_analysis() -> None:
    """Major severity should execute the complete community-impact path."""
    calls, _, _ = _execute_path(FloodSeverity.MAJOR)

    assert calls == [
        "weather",
        "forecast",
        "gis",
        "village",
        "shelter",
        "knowledge",
        "dataset",
        "recommendation",
    ]


def test_extreme_forecast_follows_the_full_evidence_path() -> None:
    """Extreme severity should use every production evidence collection node."""
    calls, _, _ = _execute_path(FloodSeverity.EXTREME)

    assert calls == [
        "weather",
        "forecast",
        "gis",
        "village",
        "shelter",
        "knowledge",
        "dataset",
        "recommendation",
    ]


def test_router_skips_gis_when_forecast_is_unavailable() -> None:
    """Unavailable forecast evidence must deterministically bypass GIS."""
    classifier = Mock()
    state = state_factory().create()

    destination = FloodSeverityRoutingPolicy(classifier).route_after_forecast(state)

    assert destination == "knowledge"
    assert state.forecast_result is None
    classifier.classify.assert_not_called()


@pytest.mark.parametrize("value", (None, "unknown"))
def test_router_skips_community_analysis_without_major_gis_evidence(
    value: str | None,
) -> None:
    """Missing or invalid GIS severity must not create an unsupported route."""
    state = (
        state_factory()
        .create()
        .model_copy(update={"gis": GISEvidence(flood_zone=value)})
    )

    destination = FloodSeverityRoutingPolicy(Mock()).route_after_gis(state)

    assert destination == "knowledge"
