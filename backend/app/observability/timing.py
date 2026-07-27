"""Reusable monotonic timing utilities for observability-only measurements."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class OperationTimer:
    """Measure an operation duration without owning execution or logging."""

    started_at: float
    clock: Callable[[], float]

    @classmethod
    def start(cls, clock: Callable[[], float] = perf_counter) -> "OperationTimer":
        """Start one monotonic timer using the supplied deterministic clock."""
        return cls(started_at=clock(), clock=clock)

    def elapsed_ms(self) -> float:
        """Return elapsed milliseconds without mutating timer state."""
        return (self.clock() - self.started_at) * 1_000
