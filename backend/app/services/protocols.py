"""Structural service contracts for loading Flood-Aware dataset tables."""

from typing import Protocol

from backend.app.data.models import DatasetTable
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterListDTO,
    VillageListDTO,
)


class DatasetServiceProtocol(Protocol):
    """Define a service contract for loading one complete dataset table."""

    def load_dataset(self) -> DatasetTable:
        """Load and return the complete dataset table served by this service."""

        ...

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return application-ready metadata and exact record statistics."""

        ...


class VillageServiceProtocol(Protocol):
    """Define a service contract for loading the configured village dataset."""

    def load_villages(self) -> VillageListDTO:
        """Load and return application-ready village records."""

        ...

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return the configured village dataset summary."""

        ...


class ShelterServiceProtocol(Protocol):
    """Define a service contract for loading the configured shelter dataset."""

    def load_shelters(self) -> ShelterListDTO:
        """Load and return application-ready shelter records."""

        ...

    def load_summary(self) -> DatasetSummaryDTO:
        """Load and return the configured shelter dataset summary."""

        ...


class DatasetCatalogServiceProtocol(Protocol):
    """Define a service contract for independent configured dataset summaries."""

    def load_catalog(self) -> DatasetCatalogDTO:
        """Load and return the catalog of configured dataset summaries."""

        ...
