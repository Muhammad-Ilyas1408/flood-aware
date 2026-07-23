"""The sole runtime component responsible for invoking registered tools."""

import logging

from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.ai.tools.exceptions import ToolExecutionError
from backend.app.ai.tools.registry import ToolRegistry


LOGGER = logging.getLogger(__name__)


class ToolExecutor:
    """Resolve and execute registered tools without planning or reasoning."""

    def __init__(self, registry: ToolRegistry) -> None:
        """Initialize the executor with an injected runtime registry.

        Args:
            registry: Directory used to resolve requested tools.
        """

        self._registry = registry

    def execute(self, tool_name: str, context: DecisionContext) -> ToolResult:
        """Execute one registered tool and return its canonical result.

        Args:
            tool_name: Name of the registered tool to invoke.
            context: Existing decision context supplied to the tool.

        Raises:
            ToolExecutionError: If the tool raises an unexpected exception.
        """

        tool = self._registry.get(tool_name)
        LOGGER.info("Executing AI tool: %s", tool_name)
        try:
            return tool.execute(context)
        except (RuntimeError, ValueError) as error:
            raise ToolExecutionError(f"Tool {tool_name!r} execution failed.") from error
