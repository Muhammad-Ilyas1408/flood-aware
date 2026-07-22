"""Deterministic orchestration for Flood-Aware AI tools."""

from backend.app.ai.models import (
    DecisionContext,
    DecisionRequest,
    DecisionResult,
    Recommendation,
    RecommendationPriority,
)
from backend.app.ai.protocols import (
    DatasetCatalogToolProtocol,
    ShelterToolProtocol,
    VillageToolProtocol,
)


class DecisionEngine:
    """Coordinate deterministic AI-tool execution for one decision request."""

    def __init__(
        self,
        village_tool: VillageToolProtocol,
        shelter_tool: ShelterToolProtocol,
        dataset_catalog_tool: DatasetCatalogToolProtocol,
    ) -> None:
        """Initialize the engine with its AI tool dependencies.

        Args:
            village_tool: The tool used to retrieve village information.
            shelter_tool: The tool used to retrieve shelter information.
            dataset_catalog_tool: The tool used to retrieve dataset catalog information.
        """

        self._village_tool: VillageToolProtocol = village_tool
        self._shelter_tool: ShelterToolProtocol = shelter_tool
        self._dataset_catalog_tool: DatasetCatalogToolProtocol = dataset_catalog_tool

    def execute(self, request: DecisionRequest) -> DecisionResult:
        """Execute the deterministic tool sequence for a decision request.

        Args:
            request: The decision request accepted by the engine contract.

        Returns:
            The assembled decision result with a placeholder recommendation.
        """

        EMPTY_EVIDENCE = ()
        EMPTY_NOTES = ()
        context_data = {
            "question": request.question,
            "scenario": request.scenario,
            "metadata": request.metadata,
        }
        initial_context = DecisionContext(
            tool_results=(),
            evidence=EMPTY_EVIDENCE,
            notes=EMPTY_NOTES,
            context=context_data,
        )
        village_result = self._village_tool.execute(initial_context)

        village_context = DecisionContext(
            tool_results=(village_result,),
            evidence=EMPTY_EVIDENCE,
            notes=EMPTY_NOTES,
            context=context_data,
        )
        shelter_result = self._shelter_tool.execute(village_context)

        shelter_context = DecisionContext(
            tool_results=(village_result, shelter_result),
            evidence=EMPTY_EVIDENCE,
            notes=EMPTY_NOTES,
            context=context_data,
        )
        dataset_catalog_result = self._dataset_catalog_tool.execute(shelter_context)

        final_context = DecisionContext(
            tool_results=(village_result, shelter_result, dataset_catalog_result),
            evidence=EMPTY_EVIDENCE,
            notes=EMPTY_NOTES,
            context=context_data,
        )
        return DecisionResult(
            context=final_context,
            recommendations=(
                Recommendation(
                    summary="Decision engine executed successfully.",
                    reasoning="AI reasoning is not yet implemented.",
                    priority=RecommendationPriority.LOW,
                    actions=(),
                ),
            ),
            evidence=EMPTY_EVIDENCE,
            tool_results=final_context.tool_results,
        )
