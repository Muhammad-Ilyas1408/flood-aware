"""Focused tests for additive production observability primitives."""

import logging

from backend.app.decision.resilience import CircuitState
from backend.app.observability.context import ExecutionContext
from backend.app.observability.health import DecisionProviderHealthTracker
from backend.app.observability.metrics import LoggingDecisionMetricsCollector
from backend.app.observability.timing import OperationTimer
from backend.app.observability.version import (
    DECISION_VERSION,
    GRAPH_VERSION,
    PROMPT_VERSION,
    SYSTEM_VERSION,
)
from backend.tests.graph_test_support import state_factory


def test_execution_context_reuses_graph_correlation_identifiers() -> None:
    """Context must project existing graph IDs rather than generate replacements."""
    state = state_factory().create()

    context = ExecutionContext.from_graph_state(state)

    assert context.execution_id == state.runtime.execution_id
    assert context.request_id == state.runtime.request_id
    assert context.log_fields()["execution_id"] == str(state.runtime.execution_id)


def test_operation_timer_uses_an_injected_monotonic_clock() -> None:
    """Timing must remain deterministic when callers inject a clock."""
    current_time = [10.0]
    timer = OperationTimer.start(clock=lambda: current_time[0])
    current_time[0] = 10.125

    assert timer.elapsed_ms() == 125.0


def test_logging_metrics_emit_safe_structured_fields(caplog) -> None:
    """Metrics should expose correlation metadata without execution payloads."""
    caplog.set_level(logging.INFO)
    context = ExecutionContext.from_graph_state(state_factory().create())
    collector = LoggingDecisionMetricsCollector()

    collector.record_provider_latency(context, model="gpt-4.1-mini", duration_ms=12.5)

    record = next(
        record
        for record in caplog.records
        if record.message == "decision_metric_provider_latency"
    )
    assert record.execution_id == str(context.execution_id)
    assert record.model == "gpt-4.1-mini"
    assert record.duration_ms == 12.5


def test_health_tracker_exposes_immutable_local_provider_state() -> None:
    """Health snapshots should report local success and circuit availability."""
    tracker = DecisionProviderHealthTracker()
    tracker.record_success()
    tracker.record_failure()

    health = tracker.snapshot(CircuitState.OPEN)

    assert health.last_success is not None
    assert health.last_failure is not None
    assert health.available is False
    assert health.circuit_state is CircuitState.OPEN


def test_version_metadata_is_centralized_and_immutable() -> None:
    """Runtime version constants must remain centralized stable metadata."""
    assert (SYSTEM_VERSION, GRAPH_VERSION, DECISION_VERSION, PROMPT_VERSION) == (
        "0.1.0",
        "v1.0.0",
        "v1.0.0",
        "v1.0.0",
    )
