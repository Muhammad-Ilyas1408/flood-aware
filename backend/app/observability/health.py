"""In-memory provider health reporting without network or persistence concerns."""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from backend.app.decision.resilience import CircuitState


@dataclass(frozen=True, slots=True)
class DecisionProviderHealth:
    """Immutable operational snapshot for one decision-provider instance.

    The snapshot reports local runtime state only. It does not probe a provider,
    make network calls, or define availability policy outside circuit state.
    """

    last_success: datetime | None
    last_failure: datetime | None
    circuit_state: CircuitState
    available: bool


class DecisionProviderHealthTracker:
    """Own mutable health observation for one provider instance only.

    State is protected by a lock, never global, and exposed solely as immutable
    snapshots for diagnostics or future health endpoints.
    """

    def __init__(self) -> None:
        """Initialize an empty healthy-provider observation state."""
        self._last_success: datetime | None = None
        self._last_failure: datetime | None = None
        self._lock = Lock()

    def record_success(self) -> None:
        """Record a successful provider request using a UTC timestamp."""
        with self._lock:
            self._last_success = datetime.now(UTC)

    def record_failure(self) -> None:
        """Record a failed provider request using a UTC timestamp."""
        with self._lock:
            self._last_failure = datetime.now(UTC)

    def snapshot(self, circuit_state: CircuitState) -> DecisionProviderHealth:
        """Return an immutable health report for the supplied circuit state."""
        with self._lock:
            return DecisionProviderHealth(
                last_success=self._last_success,
                last_failure=self._last_failure,
                circuit_state=circuit_state,
                available=circuit_state is not CircuitState.OPEN,
            )
