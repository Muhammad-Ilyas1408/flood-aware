"""Structural contracts for Flood-Aware AI tool capabilities."""

from typing import Protocol

from backend.app.ai.models import DecisionContext, ToolResult


__all__ = [
    "VillageToolProtocol",
    "ShelterToolProtocol",
    "DatasetCatalogToolProtocol",
]


class VillageToolProtocol(Protocol):
    """Define the AI capability of retrieving village information."""

    def execute(self, context: DecisionContext) -> ToolResult:
        """Return village information relevant to the supplied decision context."""

        ...


class ShelterToolProtocol(Protocol):
    """Define the AI capability of retrieving shelter information."""

    def execute(self, context: DecisionContext) -> ToolResult:
        """Return shelter information relevant to the supplied decision context."""

        ...


class DatasetCatalogToolProtocol(Protocol):
    """Define the AI capability of retrieving dataset catalog information."""

    def execute(self, context: DecisionContext) -> ToolResult:
        """Return dataset catalog information for the supplied decision context."""

        ...
