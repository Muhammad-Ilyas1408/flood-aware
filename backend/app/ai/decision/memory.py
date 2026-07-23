"""Execution-only memory for one decision runtime invocation."""

from backend.app.ai.models import ToolResult


class ExecutionMemory:
    """Store completed tool outputs and prevent duplicate execution per request."""

    def __init__(self) -> None:
        """Initialize empty state for one isolated decision execution."""

        self._results: dict[str, ToolResult] = {}

    def has_executed(self, tool_name: str) -> bool:
        """Return whether a named tool already completed in this execution."""

        return tool_name in self._results

    def record(self, result: ToolResult) -> None:
        """Store one canonical tool result using its canonical tool name."""

        self._results[result.tool_name] = result

    def results(self) -> tuple[ToolResult, ...]:
        """Return completed outputs in their chronological execution order."""

        return tuple(self._results.values())
