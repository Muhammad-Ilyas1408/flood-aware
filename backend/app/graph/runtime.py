"""Execute the immutable LangGraph evidence workflow."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import logging

from backend.app.graph.graph import GraphBuilder, GraphStep
from backend.app.graph.state import ErrorInfo, ExecutionTrace, GraphState, NodeStatus
from backend.app.core.logger import get_logger
from backend.app.observability.context import ExecutionContext
from backend.app.observability.logging import log_event
from backend.app.observability.timing import OperationTimer

_LOGGER = get_logger(__name__)


class GraphRuntime:
    """Execute a graph state without depending on legacy runtime models."""

    def __init__(
        self,
        *,
        graph_builder: GraphBuilder,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Compile one graph and inject runtime-owned trace instrumentation."""
        self._clock = clock or (lambda: datetime.now(UTC))
        self._step_names = graph_builder.step_names
        self._graph = graph_builder.compile(trace_wrapper=self._trace_step)

    async def execute(self, state: GraphState) -> GraphState:
        """Execute the graph and finalize immutable runtime trace metadata."""
        context = ExecutionContext.from_graph_state(state)
        timer = OperationTimer.start()
        log_event(
            _LOGGER,
            logging.INFO,
            "graph_execution_started",
            context,
            node="graph",
        )
        try:
            output = await self._graph.ainvoke(state)
        except Exception as error:
            log_event(
                _LOGGER,
                logging.WARNING,
                "graph_execution_failed",
                context,
                node="graph",
                duration_ms=timer.elapsed_ms(),
                failure_type=type(error).__name__,
            )
            raise
        result = self._finalize_trace(self._state_from_output(output))
        log_event(
            _LOGGER,
            logging.INFO,
            "graph_execution_finished",
            context,
            node="graph",
            duration_ms=timer.elapsed_ms(),
        )
        return result

    def _trace_step(self, node_name: str, step: GraphStep) -> GraphStep:
        """Wrap one graph callback with immutable execution-trace recording."""

        async def traced(state: GraphState) -> GraphState:
            """Execute one step and append completed, skipped, or failure trace data."""
            started_at = self._clock()
            context = ExecutionContext.from_graph_state(state)
            timer = OperationTimer.start()
            log_event(
                _LOGGER,
                logging.INFO,
                "graph_node_started",
                context,
                node=node_name,
            )
            try:
                result = await step(state)
            except Exception as error:
                log_event(
                    _LOGGER,
                    logging.WARNING,
                    "graph_node_failed",
                    context,
                    node=node_name,
                    duration_ms=timer.elapsed_ms(),
                    failure_type=type(error).__name__,
                )
                raise
            finished_at = self._clock()
            node_error = _node_error(state, result, node_name)
            skipped = result is state
            trace = ExecutionTrace(
                node_name=node_name,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(finished_at - started_at).total_seconds() * 1_000,
                status=(
                    NodeStatus.FAILED
                    if node_error is not None
                    else NodeStatus.SKIPPED if skipped else NodeStatus.COMPLETED
                ),
                retries=0,
                skipped=skipped,
                error=(
                    node_error.message
                    if node_error is not None
                    else "Node precondition was unavailable; execution was skipped."
                    if skipped
                    else None
                ),
            )
            log_event(
                _LOGGER,
                logging.INFO,
                "graph_node_finished",
                context,
                node=node_name,
                duration_ms=timer.elapsed_ms(),
            )
            return result.model_copy(
                update={"execution_trace": result.execution_trace + (trace,)}
            )

        return traced

    def _finalize_trace(self, state: GraphState) -> GraphState:
        """Append skipped steps and complete runtime metadata without mutation."""
        completed = tuple(
            trace.node_name
            for trace in state.execution_trace
            if trace.status is NodeStatus.COMPLETED
        )
        failed = {
            trace.node_name
            for trace in state.execution_trace
            if trace.status is NodeStatus.FAILED
        }
        recorded = {trace.node_name for trace in state.execution_trace}
        skipped = tuple(
            name
            for name in self._step_names
            if name not in completed and name not in failed
        )
        finished_at = self._clock()
        skipped_traces = tuple(
            ExecutionTrace(
                node_name=name,
                started_at=finished_at,
                finished_at=finished_at,
                duration_ms=0.0,
                status=NodeStatus.SKIPPED,
                retries=0,
                skipped=True,
            )
            for name in skipped
            if name not in recorded
        )
        runtime = state.runtime.model_copy(
            update={
                "completed_nodes": completed,
                "skipped_nodes": skipped,
                "finished_at": finished_at,
            }
        )
        return state.model_copy(
            update={
                "runtime": runtime,
                "execution_trace": state.execution_trace + skipped_traces,
            }
        )

    @staticmethod
    def _state_from_output(output: GraphState | Mapping[str, object]) -> GraphState:
        """Validate LangGraph output as the canonical immutable graph state."""
        if isinstance(output, GraphState):
            return output
        return GraphState.model_validate(output)


def _node_error(
    previous: GraphState, current: GraphState, node_name: str
) -> ErrorInfo | None:
    """Return the recoverable error recorded by the current node, if any."""
    new_errors = current.errors[len(previous.errors) :]
    return next(
        (error for error in reversed(new_errors) if error.source_node == node_name),
        None,
    )
