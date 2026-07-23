"""Immutable metadata contracts for registered AI tools."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """Describe one runtime AI capability without executing it.

    Attributes:
        name: Stable runtime identifier for the tool.
        description: Human-readable purpose of the tool.
        version: Version of the capability contract.
        capabilities: Explicit operations provided by the tool.
        available: Whether the capability may currently be selected.
    """

    name: str
    description: str
    version: str
    capabilities: tuple[str, ...] = ()
    available: bool = True

