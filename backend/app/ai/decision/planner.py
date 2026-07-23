"""Framework-independent decision-planning contracts and baseline behavior."""

from typing import Protocol

from backend.app.ai.decision.memory import ExecutionMemory
from backend.app.ai.tools.exceptions import PlanningError
from backend.app.ai.tools.metadata import ToolMetadata


class PlannerProtocol(Protocol):
    """Define how a runtime chooses the next tool without executing it."""

    def next_tool(
        self,
        available_tools: tuple[ToolMetadata, ...],
        memory: ExecutionMemory,
    ) -> str | None:
        """Return the next available, unexecuted tool name or ``None``."""

        ...


class SequentialPlanner:
    """Select the first available unexecuted tool in metadata order."""

    def next_tool(
        self,
        available_tools: tuple[ToolMetadata, ...],
        memory: ExecutionMemory,
    ) -> str | None:
        """Select a tool without executing it or applying domain reasoning.

        Raises:
            PlanningError: If metadata contains a blank tool name.
        """

        for metadata in available_tools:
            if not metadata.name.strip():
                raise PlanningError("Planner received blank tool metadata.")
            if metadata.available and not memory.has_executed(metadata.name):
                return metadata.name
        return None

