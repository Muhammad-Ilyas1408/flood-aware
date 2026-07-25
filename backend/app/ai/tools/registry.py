"""Registry for runtime-discoverable AI tool capabilities."""

from dataclasses import dataclass
from typing import Protocol

from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.ai.tools.exceptions import ToolNotFoundError, ToolRegistrationError
from backend.app.ai.tools.metadata import ToolMetadata


class ExecutableToolProtocol(Protocol):
    """Represent the common execution shape shared by canonical AI tools."""

    def execute(self, context: DecisionContext) -> ToolResult:
        """Execute the tool for one decision context."""

        ...


@dataclass(frozen=True, slots=True)
class _RegisteredTool:
    """Keep a runtime tool and its immutable metadata together."""

    metadata: ToolMetadata
    tool: ExecutableToolProtocol


class ToolRegistry:
    """Maintain the available AI-tool directory without invoking tools."""

    def __init__(self) -> None:
        """Initialize an empty, instance-scoped tool directory."""

        self._tools: dict[str, _RegisteredTool] = {}

    def register(self, metadata: ToolMetadata, tool: ExecutableToolProtocol) -> None:
        """Register one uniquely named executable tool.

        Args:
            metadata: Immutable capability information for the tool.
            tool: Structural canonical tool implementation.

        Raises:
            ToolRegistrationError: If the metadata name is blank or already registered.
        """

        if not metadata.name.strip():
            raise ToolRegistrationError("Tool metadata name cannot be blank.")
        if metadata.name in self._tools:
            raise ToolRegistrationError(
                f"Tool {metadata.name!r} is already registered."
            )
        self._tools[metadata.name] = _RegisteredTool(metadata=metadata, tool=tool)

    def remove(self, name: str) -> None:
        """Remove one registered tool.

        Args:
            name: Registered tool name.

        Raises:
            ToolNotFoundError: If no tool has the requested name.
        """

        if name not in self._tools:
            raise ToolNotFoundError(f"Tool {name!r} is not registered.")
        del self._tools[name]

    def get(self, name: str) -> ExecutableToolProtocol:
        """Return one registered tool without executing it.

        Args:
            name: Registered tool name.

        Raises:
            ToolNotFoundError: If no tool has the requested name.
        """

        try:
            return self._tools[name].tool
        except KeyError as error:
            raise ToolNotFoundError(f"Tool {name!r} is not registered.") from error

    def list_metadata(self) -> tuple[ToolMetadata, ...]:
        """Return metadata for all registered tools in stable name order."""

        return tuple(self._tools[name].metadata for name in sorted(self._tools))
