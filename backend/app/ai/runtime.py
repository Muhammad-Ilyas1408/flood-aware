"""Composition facade for one framework-independent AI runtime execution."""

from dataclasses import dataclass

from backend.app.ai.decision.memory import ExecutionMemory
from backend.app.ai.decision.planner import PlannerProtocol
from backend.app.ai.decision.trace import ExecutionTrace
from backend.app.ai.tools.executor import ToolExecutor
from backend.app.ai.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class AIRuntime:
    """Compose the runtime collaborators required by one decision execution.

    The facade owns no planning, tool-invocation, or domain decision behavior.
    It provides a single injected boundary through which a decision engine can
    access the independently testable runtime collaborators.

    Attributes:
        planner: Component that selects the next tool without executing it.
        executor: Component exclusively responsible for invoking tools.
        registry: Directory of registered runtime tool capabilities.
        memory: Per-execution intermediate tool-output store.
        trace: Per-execution observable lifecycle history.
    """

    planner: PlannerProtocol
    executor: ToolExecutor
    registry: ToolRegistry
    memory: ExecutionMemory
    trace: ExecutionTrace
