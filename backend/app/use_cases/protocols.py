"""Structural contracts for Flood-Aware application use cases."""

from typing import Protocol

from backend.app.dtos.datasets import DatasetCatalogDTO, ShelterListDTO, VillageListDTO
from backend.app.dtos.village_summary import VillageSummaryResultDTO

__all__ = [
    "ViewVillagesUseCaseProtocol",
    "ViewSheltersUseCaseProtocol",
    "ViewDatasetCatalogUseCaseProtocol",
    "ViewVillageSummariesUseCaseProtocol",
]


class ViewVillagesUseCaseProtocol(Protocol):
    """Define the application task of viewing configured village records."""

    def execute(self) -> VillageListDTO:
        """Return the configured village records as an immutable DTO."""

        ...


class ViewSheltersUseCaseProtocol(Protocol):
    """Define the application task of viewing configured shelter records."""

    def execute(self) -> ShelterListDTO:
        """Return the configured shelter records as an immutable DTO."""

        ...


class ViewDatasetCatalogUseCaseProtocol(Protocol):
    """Define the application task of viewing the configured dataset catalog."""

    def execute(self) -> DatasetCatalogDTO:
        """Return configured dataset summaries as an immutable DTO."""

        ...


class ViewVillageSummariesUseCaseProtocol(Protocol):
    """Define the application task of viewing lightweight village condition summaries."""

    def execute(self, village_names: tuple[str, ...]) -> VillageSummaryResultDTO:
        """Return honest condition summaries for the requested village names."""

        ...
