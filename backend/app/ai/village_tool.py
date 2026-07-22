"""Concrete AI tool for retrieving configured village data."""

from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.use_cases.protocols import ViewVillagesUseCaseProtocol


TOOL_NAME = "VillageTool"


class VillageTool:
    """Retrieve configured village data through the application use-case boundary."""

    def __init__(self, use_case: ViewVillagesUseCaseProtocol) -> None:
        """Initialize the tool with its village-viewing use case.

        Args:
            use_case: The application task used to retrieve village data.
        """

        self._use_case: ViewVillagesUseCaseProtocol = use_case

    def execute(self, context: DecisionContext) -> ToolResult:
        """Retrieve village data for a decision context.

        Args:
            context: The decision context accepted for tool-contract consistency.

        Returns:
            A tool result containing the unchanged village DTO.
        """

        dto = self._use_case.execute()
        return ToolResult(
            tool_name=TOOL_NAME,
            summary="Village dataset retrieved.",
            data=dto,
            evidence=(),
        )
