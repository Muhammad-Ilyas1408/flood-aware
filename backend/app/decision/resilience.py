"""Injected, instance-scoped resilience primitives for decision providers."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Callable


@dataclass(frozen=True, slots=True)
class DecisionRuntimeConfig:
    """Configure timeout, retry, and circuit-breaker behaviour for one provider.

    Values are validated on construction and remain immutable for the provider's
    lifetime. The configuration is intentionally independent of graph state and
    provider SDKs.
    """

    timeout_seconds: float = 30.0
    retry_count: int = 2
    base_backoff_seconds: float = 0.25
    max_backoff_seconds: float = 2.0
    jitter_seconds: float = 0.05
    circuit_breaker_threshold: int = 3
    circuit_recovery_seconds: float = 30.0

    def __post_init__(self) -> None:
        """Reject invalid runtime settings before any provider request is made."""
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative.")
        if self.base_backoff_seconds < 0 or self.max_backoff_seconds < 0:
            raise ValueError("backoff durations must not be negative.")
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValueError(
                "max_backoff_seconds must be at least base_backoff_seconds."
            )
        if self.jitter_seconds < 0:
            raise ValueError("jitter_seconds must not be negative.")
        if self.circuit_breaker_threshold < 1:
            raise ValueError("circuit_breaker_threshold must be at least one.")
        if self.circuit_recovery_seconds <= 0:
            raise ValueError("circuit_recovery_seconds must be greater than zero.")


class CircuitState(str, Enum):
    """Represent the state of one provider-local circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class DecisionExecutionMetadata:
    """Keep per-request resilience facts internal to provider execution."""

    attempt_count: int
    retry_count: int
    timeout_occurred: bool
    fallback_used: bool = False


class DecisionCircuitBreaker:
    """Protect one injected provider from repeated transient failures.

    The breaker is instance-scoped, concurrency-safe, and has no dependency on
    graph state. A single half-open probe is allowed after the recovery interval.
    """

    def __init__(
        self,
        config: DecisionRuntimeConfig,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Initialize a circuit breaker from immutable runtime configuration."""
        self._config = config
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_probe_active = False
        self._lock = asyncio.Lock()

    async def allow_request(self) -> bool:
        """Return whether one provider request may proceed at this time."""
        async with self._lock:
            if self._state is CircuitState.CLOSED:
                return True
            if self._state is CircuitState.OPEN:
                if not self._recovery_interval_elapsed():
                    return False
                self._state = CircuitState.HALF_OPEN
            if self._half_open_probe_active:
                return False
            self._half_open_probe_active = True
            return True

    async def record_success(self) -> None:
        """Close the circuit after a successful provider request or probe."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None
            self._half_open_probe_active = False

    async def record_failure(self) -> None:
        """Record a final transient failure and open the circuit when required."""
        async with self._lock:
            self._half_open_probe_active = False
            self._failure_count += 1
            if (
                self._state is CircuitState.HALF_OPEN
                or self._failure_count >= self._config.circuit_breaker_threshold
            ):
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()

    @property
    def state(self) -> CircuitState:
        """Expose the current state for deterministic diagnostics and tests."""
        return self._state

    def _recovery_interval_elapsed(self) -> bool:
        """Return whether an open circuit may permit one recovery probe."""
        return (
            self._opened_at is not None
            and self._clock() - self._opened_at >= self._config.circuit_recovery_seconds
        )
