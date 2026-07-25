"""Concrete AI tool for retrieving configured shelter data."""

from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.use_cases.protocols import ViewSheltersUseCaseProtocol

TOOL_NAME = "ShelterTool"


class ShelterTool:
    """Retrieve configured shelter data through the application use-case boundary."""

    def __init__(self, use_case: ViewSheltersUseCaseProtocol) -> None:
        """Initialize the tool with its shelter-viewing use case.

        Args:
            use_case: The application task used to retrieve shelter data.
        """

        self._use_case: ViewSheltersUseCaseProtocol = use_case

    def execute(self, context: DecisionContext) -> ToolResult:
        """Retrieve shelter data for a decision context.

        Args:
            context: The decision context accepted for tool-contract consistency.

        Returns:
            A tool result containing the unchanged shelter DTO.
        """

        dto = self._use_case.execute()
        return ToolResult(
            tool_name=TOOL_NAME,
            summary="Shelter dataset retrieved.",
            data=dto,
            evidence=(),
        )
