"""Contract tests for deterministic AI decision-engine orchestration."""

from unittest.mock import create_autospec

from backend.app.ai.decision_engine import DecisionEngine
from backend.app.ai.models import (
    DecisionContext,
    DecisionRequest,
    DecisionResult,
    Recommendation,
    RecommendationPriority,
    ToolResult,
)
from backend.app.ai.protocols import (
    DatasetCatalogToolProtocol,
    ShelterToolProtocol,
    VillageToolProtocol,
)


def _decision_request() -> DecisionRequest:
    """Create a representative immutable request for contract tests."""
    return DecisionRequest(
        question="Which resources are available?",
        scenario="Flood response planning.",
        metadata={"district": "Swat"},
    )


def _tool_results() -> tuple[ToolResult, ToolResult, ToolResult]:
    """Create distinct tool results used to verify identity preservation."""
    return (
        ToolResult(tool_name="VillageTool", summary="Village result."),
        ToolResult(tool_name="ShelterTool", summary="Shelter result."),
        ToolResult(tool_name="DatasetCatalogTool", summary="Catalog result."),
    )


def _decision_engine(
    village_tool: VillageToolProtocol,
    shelter_tool: ShelterToolProtocol,
    dataset_catalog_tool: DatasetCatalogToolProtocol,
) -> DecisionEngine:
    """Construct an engine with isolated protocol-based tool dependencies."""
    return DecisionEngine(village_tool, shelter_tool, dataset_catalog_tool)


def _configured_tools(
    village_result: ToolResult,
    shelter_result: ToolResult,
    dataset_catalog_result: ToolResult,
) -> tuple[
    VillageToolProtocol,
    ShelterToolProtocol,
    DatasetCatalogToolProtocol,
]:
    """Create autospecced tools configured with supplied immutable results."""
    village_tool = create_autospec(
        VillageToolProtocol,
        instance=True,
        spec_set=True,
    )
    shelter_tool = create_autospec(
        ShelterToolProtocol,
        instance=True,
        spec_set=True,
    )
    dataset_catalog_tool = create_autospec(
        DatasetCatalogToolProtocol,
        instance=True,
        spec_set=True,
    )
    village_tool.execute.return_value = village_result
    shelter_tool.execute.return_value = shelter_result
    dataset_catalog_tool.execute.return_value = dataset_catalog_result
    return village_tool, shelter_tool, dataset_catalog_tool


def test_decision_engine_calls_village_tool_once() -> None:
    """The engine invokes the village capability exactly once."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
        _decision_request()
    )

    village_tool.execute.assert_called_once()


def test_decision_engine_calls_shelter_tool_once() -> None:
    """The engine invokes the shelter capability exactly once."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
        _decision_request()
    )

    shelter_tool.execute.assert_called_once()


def test_decision_engine_calls_dataset_catalog_tool_once() -> None:
    """The engine invokes the dataset-catalog capability exactly once."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
        _decision_request()
    )

    dataset_catalog_tool.execute.assert_called_once()


def test_shelter_tool_context_contains_village_result() -> None:
    """The shelter capability receives the original village result in context."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
        _decision_request()
    )

    context = shelter_tool.execute.call_args.args[0]
    assert isinstance(context, DecisionContext)
    assert any(result is village_result for result in context.tool_results)


def test_dataset_catalog_tool_context_contains_accumulated_results() -> None:
    """The catalog capability receives the original prior tool results in context."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
        _decision_request()
    )

    context = dataset_catalog_tool.execute.call_args.args[0]
    assert isinstance(context, DecisionContext)
    assert any(result is village_result for result in context.tool_results)
    assert any(result is shelter_result for result in context.tool_results)


def test_decision_engine_returns_complete_decision_result() -> None:
    """The engine returns the immutable aggregate decision contract."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    result = _decision_engine(
        village_tool,
        shelter_tool,
        dataset_catalog_tool,
    ).execute(_decision_request())

    assert isinstance(result, DecisionResult)
    assert isinstance(result.context, DecisionContext)
    assert isinstance(result.recommendations, tuple)
    assert isinstance(result.tool_results, tuple)


def test_decision_engine_returns_original_tool_results() -> None:
    """The result exposes every original tool result without ordering assumptions."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    result = _decision_engine(
        village_tool,
        shelter_tool,
        dataset_catalog_tool,
    ).execute(_decision_request())

    assert any(item is village_result for item in result.tool_results)
    assert any(item is shelter_result for item in result.tool_results)
    assert any(item is dataset_catalog_result for item in result.tool_results)


def test_decision_engine_returns_placeholder_recommendation() -> None:
    """The current decision contract includes its documented placeholder recommendation."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    result = _decision_engine(
        village_tool,
        shelter_tool,
        dataset_catalog_tool,
    ).execute(_decision_request())

    recommendation = result.recommendations[0]
    assert isinstance(recommendation, Recommendation)
    assert recommendation.summary == "Decision engine executed successfully."
    assert recommendation.reasoning == "AI reasoning is not yet implemented."
    assert recommendation.priority is RecommendationPriority.LOW


def test_decision_engine_preserves_request_context_values() -> None:
    """The result context preserves the request's documented contextual values."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )
    request = _decision_request()

    result = _decision_engine(
        village_tool,
        shelter_tool,
        dataset_catalog_tool,
    ).execute(request)

    assert result.context.context == {
        "question": request.question,
        "scenario": request.scenario,
        "metadata": request.metadata,
    }


def test_decision_engine_preserves_tool_result_identity() -> None:
    """The engine returns the exact objects produced by each tool."""
    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )

    result = _decision_engine(
        village_tool,
        shelter_tool,
        dataset_catalog_tool,
    ).execute(_decision_request())

    assert any(item is village_result for item in result.tool_results)
    assert any(item is shelter_result for item in result.tool_results)
    assert any(item is dataset_catalog_result for item in result.tool_results)


def test_decision_engine_propagates_tool_failure() -> None:
    """The engine preserves the current contract of propagating tool failures."""
    import pytest

    village_result, shelter_result, dataset_catalog_result = _tool_results()
    village_tool, shelter_tool, dataset_catalog_tool = _configured_tools(
        village_result,
        shelter_result,
        dataset_catalog_result,
    )
    village_tool.execute.side_effect = RuntimeError("Village tool failed.")

    with pytest.raises(RuntimeError, match="Village tool failed."):
        _decision_engine(village_tool, shelter_tool, dataset_catalog_tool).execute(
            _decision_request()
        )
