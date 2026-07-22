"""Dependency composition for Flood-Aware AI tools."""

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.protocols import (
    DatasetCatalogToolProtocol,
    ShelterToolProtocol,
    VillageToolProtocol,
)
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.composition import (
    get_dataset_catalog_use_case,
    get_shelter_use_case,
    get_village_use_case,
)


def get_village_tool(request) -> VillageToolProtocol:
    """Provide the village AI tool composed from the village use case."""
    return VillageTool(get_village_use_case(request))


def get_shelter_tool(request) -> ShelterToolProtocol:
    """Provide the shelter AI tool composed from the shelter use case."""
    return ShelterTool(get_shelter_use_case(request))


def get_dataset_catalog_tool(request) -> DatasetCatalogToolProtocol:
    """Provide the dataset catalog AI tool composed from its use case."""
    return DatasetCatalogTool(get_dataset_catalog_use_case(request))
