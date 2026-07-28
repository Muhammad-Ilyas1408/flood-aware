"""Provider-independent decision-agent contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from backend.app.decision.models import Decision

if TYPE_CHECKING:
    from backend.app.graph.state import EvidenceBundle
    from backend.app.observability.context import ExecutionContext


class ConversationTurnLike(Protocol):
    """Describe the bounded prior-turn data needed for prompt continuity."""

    request_text: str

    @property
    def recommendation_summary(self) -> str:
        """Return the prior turn's compact recommendation summary."""


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
        history: Sequence[ConversationTurnLike] = (),
    ) -> Decision:
        """Return a validated decision with optional correlated prior turns."""
