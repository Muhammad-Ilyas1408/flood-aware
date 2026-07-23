"""Execution-only runtime trace contracts without reasoning content."""

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.app.ai.decision.state import DecisionState


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Record one observable lifecycle transition or tool invocation."""

    state: DecisionState
    occurred_at: datetime
    tool_name: str | None = None


class ExecutionTrace:
    """Collect execution history for one decision request without storing reasoning."""

    def __init__(self) -> None:
        """Initialize an empty trace for one isolated execution."""

        self._events: list[TraceEvent] = []

    def record(self, state: DecisionState, tool_name: str | None = None) -> None:
        """Append one timestamped state transition or tool execution event."""

        self._events.append(
            TraceEvent(state=state, occurred_at=datetime.now(UTC), tool_name=tool_name)
        )

    def events(self) -> tuple[TraceEvent, ...]:
        """Return immutable trace events in their observed order."""

        return tuple(self._events)
