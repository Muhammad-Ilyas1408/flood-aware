"""Immutable correlation context derived from existing graph execution state."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.app.graph.state import GraphState
from backend.app.observability.version import VersionMetadata


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Carry existing correlation and version metadata across execution boundaries.

    The context never creates identifiers or contains request payloads. It is a
    read-only projection of graph-owned runtime metadata for logging and metrics.
    """

    execution_id: UUID | None
    request_id: UUID | None
    started_at: datetime | None
    versions: VersionMetadata
    environment: str | None = None

    @classmethod
    def from_graph_state(cls, state: GraphState) -> "ExecutionContext":
        """Project one graph state's existing correlation data without mutation."""
        return cls(
            execution_id=state.runtime.execution_id,
            request_id=state.runtime.request_id,
            started_at=state.runtime.started_at,
            versions=VersionMetadata(
                graph=state.runtime.graph_version,
            ),
            environment=state.metadata.environment,
        )

    @classmethod
    def uncorrelated(cls) -> "ExecutionContext":
        """Represent a direct provider invocation without manufacturing an ID."""
        return cls(
            execution_id=None,
            request_id=None,
            started_at=None,
            versions=VersionMetadata(),
        )

    def log_fields(self) -> dict[str, object]:
        """Return non-sensitive structured fields for logs and metrics."""
        return {
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "request_id": str(self.request_id) if self.request_id else None,
            "system_version": self.versions.system,
            "graph_version": self.versions.graph,
            "decision_version": self.versions.decision,
            "prompt_version": self.versions.prompt,
            "environment": self.environment,
        }
