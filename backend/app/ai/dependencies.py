"""Dependency composition for canonical AI tools and the AI runtime."""

from fastapi import Request

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.decision.memory import ExecutionMemory
from backend.app.ai.decision.planner import SequentialPlanner
from backend.app.ai.decision.trace import ExecutionTrace
from backend.app.ai.protocols import (
    DatasetCatalogToolProtocol,
    ShelterToolProtocol,
    VillageToolProtocol,
)
from backend.app.ai.runtime import AIRuntime
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.tools.executor import ToolExecutor
from backend.app.ai.tools.metadata import ToolMetadata
from backend.app.ai.tools.registry import ToolRegistry
from backend.app.ai.village_tool import VillageTool
from backend.app.composition import (
    get_dataset_catalog_use_case,
    get_shelter_use_case,
    get_village_use_case,
)


def get_village_tool(request: Request) -> VillageToolProtocol:
    """Provide the village AI tool composed from the village use case."""
    return VillageTool(get_village_use_case(request))


def get_shelter_tool(request: Request) -> ShelterToolProtocol:
    """Provide the shelter AI tool composed from the shelter use case."""
    return ShelterTool(get_shelter_use_case(request))


def get_dataset_catalog_tool(request: Request) -> DatasetCatalogToolProtocol:
    """Provide the dataset catalog AI tool composed from its use case."""
    return DatasetCatalogTool(get_dataset_catalog_use_case(request))


def get_ai_runtime(request: Request) -> AIRuntime:
    """Compose one runtime with the registered canonical AI tools.

    Args:
        request: FastAPI request used by the existing composition providers.

    Returns:
        A per-request runtime containing the canonical tools and collaborators.
    """

    registry = ToolRegistry()
    registry.register(
        ToolMetadata(
            name="VillageTool",
            description="Retrieve configured village information.",
            version="1.0.0",
            capabilities=("villages",),
        ),
        get_village_tool(request),
    )
    registry.register(
        ToolMetadata(
            name="ShelterTool",
            description="Retrieve configured shelter information.",
            version="1.0.0",
            capabilities=("shelters",),
        ),
        get_shelter_tool(request),
    )
    registry.register(
        ToolMetadata(
            name="DatasetCatalogTool",
            description="Retrieve the configured dataset catalog.",
            version="1.0.0",
            capabilities=("dataset_catalog",),
        ),
        get_dataset_catalog_tool(request),
    )
    return AIRuntime(
        planner=SequentialPlanner(),
        executor=ToolExecutor(registry),
        registry=registry,
        memory=ExecutionMemory(),
        trace=ExecutionTrace(),
    )
