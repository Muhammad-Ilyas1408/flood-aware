"""Provider-independent decision-agent contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from backend.app.decision.models import Decision

if TYPE_CHECKING:
    from backend.app.graph.state import EvidenceBundle
    from backend.app.observability.context import ExecutionContext


class DecisionAgentProtocol(Protocol):
    """Provider abstraction for structured decisions from canonical evidence.

    Graph code depends on this contract rather than a provider SDK or any concrete
    decision-provider implementation.
    """

    async def decide(
        self,
        evidence: EvidenceBundle,
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Decision:
        """Return a validated decision, optionally correlated to one execution."""
