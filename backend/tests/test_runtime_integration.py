"""Runtime registration and execution tests for canonical AI tools."""

from unittest.mock import create_autospec, patch

from fastapi import Request

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.dependencies import get_ai_runtime
from backend.app.ai.models import DecisionContext, ToolResult
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.tools.exceptions import ToolNotFoundError, ToolRegistrationError
from backend.app.ai.tools.executor import ToolExecutor
from backend.app.ai.tools.metadata import ToolMetadata
from backend.app.ai.tools.registry import ExecutableToolProtocol, ToolRegistry
from backend.app.ai.village_tool import VillageTool
from backend.app.config.datasets import create_production_dataset_catalog_config
from backend.app.dtos.datasets import DatasetCatalogDTO, ShelterListDTO, VillageListDTO
from backend.app.main import create_application
from backend.app.use_cases.protocols import (
    ViewDatasetCatalogUseCaseProtocol,
    ViewSheltersUseCaseProtocol,
    ViewVillagesUseCaseProtocol,
)


def _production_runtime():
    """Compose the real runtime against the checked-in production CSV datasets."""

    configuration = create_production_dataset_catalog_config()
    application = create_application(configuration)
    request = Request(
        {
            "type": "http",
            "app": application,
            "method": "GET",
            "path": "/",
            "headers": [],
        }
    )
    return get_ai_runtime(request)


def test_registry_registers_and_resolves_canonical_tools() -> None:
    """The registry exposes a canonical tool by its runtime metadata name."""
    tool = create_autospec(ExecutableToolProtocol, instance=True, spec_set=True)
    registry = ToolRegistry()
    metadata = ToolMetadata("VillageTool", "Village data.", "1.0.0")

    registry.register(metadata, tool)

    assert registry.get("VillageTool") is tool
    assert registry.list_metadata() == (metadata,)


def test_registry_rejects_duplicate_registration() -> None:
    """The registry protects each canonical capability from duplicate names."""
    tool = create_autospec(ExecutableToolProtocol, instance=True, spec_set=True)
    registry = ToolRegistry()
    metadata = ToolMetadata("VillageTool", "Village data.", "1.0.0")
    registry.register(metadata, tool)

    try:
        registry.register(metadata, tool)
    except ToolRegistrationError:
        pass
    else:
        raise AssertionError("Duplicate tool registration must fail.")


def test_executor_runs_village_tool_through_its_use_case() -> None:
    """The executor returns the canonical result produced by the canonical tool."""
    use_case = create_autospec(
        ViewVillagesUseCaseProtocol, instance=True, spec_set=True
    )
    dto = VillageListDTO(villages=())
    use_case.execute.return_value = dto
    village_tool = VillageTool(use_case)
    registry = ToolRegistry()
    registry.register(
        ToolMetadata("VillageTool", "Village data.", "1.0.0"), village_tool
    )

    result = ToolExecutor(registry).execute("VillageTool", DecisionContext())

    use_case.execute.assert_called_once_with()
    assert isinstance(result, ToolResult)
    assert result.tool_name == "VillageTool"
    assert result.data is dto


def test_executor_runs_shelter_tool_through_its_use_case() -> None:
    """The executor returns the canonical shelter result from its use case."""
    use_case = create_autospec(
        ViewSheltersUseCaseProtocol, instance=True, spec_set=True
    )
    dto = ShelterListDTO(shelters=())
    use_case.execute.return_value = dto
    registry = ToolRegistry()
    registry.register(
        ToolMetadata("ShelterTool", "Shelter data.", "1.0.0"), ShelterTool(use_case)
    )

    result = ToolExecutor(registry).execute("ShelterTool", DecisionContext())

    use_case.execute.assert_called_once_with()
    assert result.tool_name == "ShelterTool"
    assert result.data is dto


def test_executor_runs_catalog_tool_through_its_use_case() -> None:
    """The executor returns the canonical catalog result from its use case."""
    use_case = create_autospec(
        ViewDatasetCatalogUseCaseProtocol,
        instance=True,
        spec_set=True,
    )
    catalog = object()
    use_case.execute.return_value = catalog
    registry = ToolRegistry()
    registry.register(
        ToolMetadata("DatasetCatalogTool", "Catalog data.", "1.0.0"),
        DatasetCatalogTool(use_case),
    )

    result = ToolExecutor(registry).execute("DatasetCatalogTool", DecisionContext())

    use_case.execute.assert_called_once_with()
    assert result.tool_name == "DatasetCatalogTool"
    assert result.data is catalog


def test_runtime_provider_registers_all_canonical_tools() -> None:
    """The composition provider assembles a runtime with all canonical tools."""
    village_tool = create_autospec(ExecutableToolProtocol, instance=True, spec_set=True)
    shelter_tool = create_autospec(ExecutableToolProtocol, instance=True, spec_set=True)
    catalog_tool = create_autospec(ExecutableToolProtocol, instance=True, spec_set=True)

    with (
        patch(
            "backend.app.ai.dependencies.get_village_tool", return_value=village_tool
        ),
        patch(
            "backend.app.ai.dependencies.get_shelter_tool", return_value=shelter_tool
        ),
        patch(
            "backend.app.ai.dependencies.get_dataset_catalog_tool",
            return_value=catalog_tool,
        ),
    ):
        runtime = get_ai_runtime(object())  # type: ignore[arg-type]

    assert tuple(item.name for item in runtime.registry.list_metadata()) == (
        "DatasetCatalogTool",
        "ShelterTool",
        "VillageTool",
    )
    assert runtime.registry.get("VillageTool") is village_tool
    assert runtime.registry.get("ShelterTool") is shelter_tool
    assert runtime.registry.get("DatasetCatalogTool") is catalog_tool


def test_runtime_executes_village_tool_with_production_dataset() -> None:
    """The real runtime returns a nonempty village DTO from production data."""

    runtime = _production_runtime()

    result = runtime.executor.execute("VillageTool", DecisionContext())

    assert isinstance(result, ToolResult)
    assert result.tool_name == "VillageTool"
    assert isinstance(result.data, VillageListDTO)
    assert result.data.villages


def test_runtime_executes_shelter_tool_with_production_dataset() -> None:
    """The real runtime returns a nonempty shelter DTO from production data."""

    runtime = _production_runtime()

    result = runtime.executor.execute("ShelterTool", DecisionContext())

    assert isinstance(result, ToolResult)
    assert result.tool_name == "ShelterTool"
    assert isinstance(result.data, ShelterListDTO)
    assert result.data.shelters


def test_runtime_executes_catalog_tool_with_production_datasets() -> None:
    """The real runtime returns catalog summaries for both production datasets."""

    runtime = _production_runtime()

    result = runtime.executor.execute("DatasetCatalogTool", DecisionContext())

    assert isinstance(result, ToolResult)
    assert result.tool_name == "DatasetCatalogTool"
    assert isinstance(result.data, DatasetCatalogDTO)
    assert result.data.villages.statistics.record_count > 0
    assert result.data.shelters.statistics.record_count > 0


def test_production_runtime_registers_and_resolves_canonical_tools() -> None:
    """The composed runtime exposes each real canonical tool by its public name."""

    runtime = _production_runtime()

    assert {metadata.name for metadata in runtime.registry.list_metadata()} == {
        "VillageTool",
        "ShelterTool",
        "DatasetCatalogTool",
    }
    assert isinstance(runtime.registry.get("VillageTool"), VillageTool)
    assert isinstance(runtime.registry.get("ShelterTool"), ShelterTool)
    assert isinstance(runtime.registry.get("DatasetCatalogTool"), DatasetCatalogTool)


def test_production_runtime_executes_canonical_tools_sequentially() -> None:
    """Sequential real tool execution leaves the runtime usable for each tool."""

    runtime = _production_runtime()
    context = DecisionContext()

    results = tuple(
        runtime.executor.execute(tool_name, context)
        for tool_name in ("VillageTool", "ShelterTool", "DatasetCatalogTool")
    )

    assert tuple(result.tool_name for result in results) == (
        "VillageTool",
        "ShelterTool",
        "DatasetCatalogTool",
    )


def test_production_runtime_tools_preserve_decision_context() -> None:
    """Canonical tools do not mutate the decision context supplied to execution."""

    runtime = _production_runtime()
    context = DecisionContext(notes=("preserve this context",))

    for tool_name in ("VillageTool", "ShelterTool", "DatasetCatalogTool"):
        runtime.executor.execute(tool_name, context)

    assert context == DecisionContext(notes=("preserve this context",))


def test_production_runtime_rejects_unknown_tool_without_registration_change() -> None:
    """An unknown-tool failure leaves the real runtime registry unchanged."""

    runtime = _production_runtime()
    registered_tools = runtime.registry.list_metadata()

    try:
        runtime.executor.execute("UnknownTool", DecisionContext())
    except ToolNotFoundError:
        pass
    else:
        raise AssertionError("Unknown runtime tools must raise ToolNotFoundError.")

    assert runtime.registry.list_metadata() == registered_tools
