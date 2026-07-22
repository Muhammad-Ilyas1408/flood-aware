"""Concrete AI tool for retrieving the configured dataset catalog."""

from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.use_cases.protocols import ViewDatasetCatalogUseCaseProtocol


TOOL_NAME = "DatasetCatalogTool"


class DatasetCatalogTool:
    """Retrieve the configured dataset catalog through the application boundary."""

    def __init__(self, use_case: ViewDatasetCatalogUseCaseProtocol) -> None:
        """Initialize the tool with its dataset-catalog use case.

        Args:
            use_case: The application task used to retrieve the dataset catalog.
        """

        self._use_case: ViewDatasetCatalogUseCaseProtocol = use_case

    def execute(self, context: DecisionContext) -> ToolResult:
        """Retrieve the dataset catalog for a decision context.

        Args:
            context: The decision context accepted for tool-contract consistency.

        Returns:
            A tool result containing the unchanged dataset catalog DTO.
        """

        dto = self._use_case.execute()
        return ToolResult(
            tool_name=TOOL_NAME,
            summary="Dataset catalog retrieved.",
            data=dto,
            evidence=(),
        )
