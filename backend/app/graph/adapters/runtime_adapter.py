"""Select a runtime strategy without modifying the existing AIRuntime."""

from enum import Enum

from backend.app.ai.models import (
    DecisionContext,
    Recommendation,
    RecommendationPriority,
)
from backend.app.graph.contracts import (
    GraphRuntimeProtocol,
    SequentialRuntimeProtocol,
)
from backend.app.graph.mapper import DecisionContextMapper
from backend.app.graph.state import GraphState


class RuntimeSelection(str, Enum):
    """Represent the architecture-approved runtime selection values."""

    SEQUENTIAL = "sequential"
    GRAPH = "graph"
    AUTO = "auto"


class RuntimeAdapter:
    """Provide one injectable selection boundary for compatible runtimes."""

    def __init__(
        self,
        *,
        sequential_runtime: SequentialRuntimeProtocol,
        graph_runtime: GraphRuntimeProtocol,
        context_mapper: DecisionContextMapper,
        selection: RuntimeSelection = RuntimeSelection.SEQUENTIAL,
    ) -> None:
        """Initialize explicitly injected runtime strategies and selection."""
        self._sequential_runtime = sequential_runtime
        self._graph_runtime = graph_runtime
        self._context_mapper = context_mapper
        self._selection = selection

    async def execute(self, context: DecisionContext) -> Recommendation:
        """Execute exactly one selected runtime strategy."""
        if self._selection is RuntimeSelection.GRAPH:
            state = self._context_mapper.map(context)
            return self._recommendation_from_state(
                await self._graph_runtime.execute(state)
            )
        return await self._sequential_runtime.execute(context)

    @staticmethod
    def _recommendation_from_state(state: GraphState) -> Recommendation:
        """Adapt internal recommendation evidence to the legacy public model."""
        priority = state.recommendation.evacuation_priority
        return Recommendation(
            summary=state.recommendation.recommendation
            or "LangGraph foundation completed without recommendation reasoning.",
            reasoning=state.recommendation.rationale,
            priority=RecommendationPriority(priority) if priority is not None else None,
            actions=state.recommendation.recommended_actions,
        )
