"""Focused tests for graph construction, runtime, and adapter behavior."""

import asyncio

from backend.app.ai.models import DecisionContext, Recommendation
from backend.app.graph.adapters.runtime_adapter import RuntimeAdapter, RuntimeSelection
from backend.app.graph.mapper import DecisionContextMapper
from backend.app.graph.nodes import DormantGraphNode
from backend.app.graph.runtime import GraphRuntime
from backend.app.graph.state import GraphState, NodeStatus, RecommendationEvidence
from backend.tests.graph_test_support import dormant_graph_builder, state_factory


def test_dormant_node_returns_the_original_immutable_state() -> None:
    """A dormant test node must not perform work or mutate graph state."""
    state = state_factory().create()
    assert asyncio.run(DormantGraphNode().execute(state)) is state


def test_graph_builder_compiles_and_executes_injected_nodes() -> None:
    """The builder should propagate one valid graph state through injected nodes."""
    state = state_factory().create()
    output = asyncio.run(dormant_graph_builder().compile().ainvoke(state))

    assert output["runtime"] == state.runtime
    assert "recommendation" in dormant_graph_builder().compile().nodes


def test_graph_runtime_executes_without_legacy_runtime_integration() -> None:
    """The isolated runtime should execute the explicitly supplied graph."""
    state = asyncio.run(
        GraphRuntime(graph_builder=dormant_graph_builder()).execute(
            state_factory().create()
        )
    )
    assert isinstance(state, GraphState)


def test_graph_runtime_records_completed_and_skipped_steps() -> None:
    """Runtime-owned trace should expose deterministic routed execution facts."""
    timestamp = state_factory().create().runtime.started_at
    state = asyncio.run(
        GraphRuntime(
            graph_builder=dormant_graph_builder(),
            clock=lambda: timestamp,
        ).execute(state_factory().create())
    )

    assert state.runtime.completed_nodes == (
        "weather",
        "forecast",
        "knowledge",
        "dataset",
        "aggregate",
        "recommendation",
    )
    assert state.runtime.skipped_nodes == ("gis", "village", "shelter")
    assert [trace.status for trace in state.execution_trace] == [
        NodeStatus.COMPLETED,
        NodeStatus.COMPLETED,
        NodeStatus.COMPLETED,
        NodeStatus.COMPLETED,
        NodeStatus.COMPLETED,
        NodeStatus.COMPLETED,
        NodeStatus.SKIPPED,
        NodeStatus.SKIPPED,
        NodeStatus.SKIPPED,
    ]


class FakeRuntime:
    """Provide deterministic legacy runtime output for adapter tests."""

    def __init__(self, summary: str) -> None:
        self._summary = summary

    async def execute(self, context: DecisionContext) -> Recommendation:
        """Return a predictable public recommendation."""
        del context
        return Recommendation(summary=self._summary)


def test_runtime_adapter_preserves_explicit_runtime_selection() -> None:
    """The adapter must execute exactly the explicitly selected runtime."""
    adapter = RuntimeAdapter(
        sequential_runtime=FakeRuntime("sequential"),
        graph_runtime=GraphRuntime(graph_builder=dormant_graph_builder()),
        context_mapper=DecisionContextMapper(state_factory()),
        selection=RuntimeSelection.SEQUENTIAL,
    )
    assert asyncio.run(adapter.execute(DecisionContext())).summary == "sequential"


def test_runtime_adapter_adapts_graph_state_to_legacy_recommendation() -> None:
    """Only the adapter converts graph output to the legacy public model."""
    adapter = RuntimeAdapter(
        sequential_runtime=FakeRuntime("sequential"),
        graph_runtime=GraphRuntime(graph_builder=dormant_graph_builder()),
        context_mapper=DecisionContextMapper(state_factory()),
        selection=RuntimeSelection.GRAPH,
    )
    assert asyncio.run(adapter.execute(DecisionContext())).summary == (
        "LangGraph foundation completed without recommendation reasoning."
    )


def test_runtime_adapter_preserves_generated_actions_and_priority() -> None:
    """The legacy boundary should retain graph recommendation output faithfully."""
    state = (
        state_factory()
        .create()
        .model_copy(
            update={
                "recommendation": RecommendationEvidence(
                    recommendation="Prepare response.",
                    rationale="Flood evidence is elevated.",
                    evacuation_priority="high",
                    recommended_actions=("Notify response teams.",),
                )
            }
        )
    )

    class GraphRuntimeDouble:
        """Return a fixed graph state without executing external dependencies."""

        async def execute(self, input_state: GraphState) -> GraphState:
            """Ignore the mapped input and return the prepared output state."""
            del input_state
            return state

    adapter = RuntimeAdapter(
        sequential_runtime=FakeRuntime("sequential"),
        graph_runtime=GraphRuntimeDouble(),
        context_mapper=DecisionContextMapper(state_factory()),
        selection=RuntimeSelection.GRAPH,
    )

    recommendation = asyncio.run(adapter.execute(DecisionContext()))

    assert recommendation.actions == ("Notify response teams.",)
    assert recommendation.priority is not None
    assert recommendation.priority.value == "high"
