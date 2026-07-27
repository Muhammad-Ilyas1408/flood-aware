"""Protocol contracts for the isolated LangGraph runtime."""

from typing import Protocol

from backend.app.ai.models import DecisionContext, Recommendation
from backend.app.graph.state import GraphState


class GraphNodeProtocol(Protocol):
    """Define the required contract for one graph node."""

    async def execute(self, state: GraphState) -> GraphState:
        """Return a new immutable graph state from one input state."""


class GraphRuntimeProtocol(Protocol):
    """Define graph execution using only canonical graph state."""

    async def execute(self, state: GraphState) -> GraphState:
        """Execute a graph workflow and return its immutable output state."""


class SequentialRuntimeProtocol(Protocol):
    """Define the legacy runtime contract retained during migration."""

    async def execute(self, context: DecisionContext) -> Recommendation:
        """Execute legacy orchestration and return the public recommendation."""


class RouterProtocol(Protocol):
    """Define deterministic graph routing without tool execution."""

    def route_after_forecast(self, state: GraphState) -> str:
        """Return the next node after deterministic forecast evaluation."""

    def route_after_gis(self, state: GraphState) -> str:
        """Return the next node after deterministic GIS evaluation."""


class EvidenceAggregatorProtocol(Protocol):
    """Define immutable evidence-bundle aggregation."""

    async def aggregate(self, state: GraphState) -> GraphState:
        """Return a state containing an aggregated evidence bundle."""


class RecommendationEngineProtocol(Protocol):
    """Define future conversion of evidence into recommendation evidence."""

    async def recommend(self, state: GraphState) -> GraphState:
        """Return a state containing recommendation evidence."""
