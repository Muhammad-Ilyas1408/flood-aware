"""Structural service contracts for loading Flood-Aware dataset tables."""

from typing import Protocol

from backend.app.data.models import DatasetTable


class DatasetServiceProtocol(Protocol):
    """Define a service contract for loading one complete dataset table."""

    def load_dataset(self) -> DatasetTable:
        """Load and return the complete dataset table served by this service."""

        ...


class VillageServiceProtocol(Protocol):
    """Define a service contract for loading the configured village dataset."""

    def load_villages(self) -> DatasetTable:
        """Load and return the complete village dataset table."""

        ...


class ShelterServiceProtocol(Protocol):
    """Define a service contract for loading the configured shelter dataset."""

    def load_shelters(self) -> DatasetTable:
        """Load and return the complete shelter dataset table."""

        ...
