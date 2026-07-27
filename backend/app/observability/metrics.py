"""Provider-independent decision metrics contracts and logging implementation."""

import logging
from typing import Protocol

from backend.app.core.logger import get_logger
from backend.app.observability.context import ExecutionContext
from backend.app.observability.logging import log_event


class DecisionMetricsCollector(Protocol):
    """Record decision execution measurements without selecting an exporter.

    Implementations own export mechanics only. Providers and graph nodes report
    operational facts through this contract and remain independent of Prometheus,
    OpenTelemetry, or any dashboard implementation.
    """

    def record_provider_latency(
        self, context: ExecutionContext, *, model: str, duration_ms: float
    ) -> None:
        """Record provider latency for one completed provider request."""

    def record_retry(self, context: ExecutionContext, *, retry_count: int) -> None:
        """Record retries attempted for one provider request."""

    def record_timeout(self, context: ExecutionContext) -> None:
        """Record that a provider request exceeded its configured timeout."""

    def record_success(self, context: ExecutionContext, *, model: str) -> None:
        """Record a successful provider request."""

    def record_failure(self, context: ExecutionContext, *, failure_type: str) -> None:
        """Record a provider failure classification."""

    def record_fallback(self, context: ExecutionContext) -> None:
        """Record use of the deterministic recommendation fallback."""

    def record_tokens(self, context: ExecutionContext, *, token_count: int) -> None:
        """Record provider token usage when it is available."""

    def record_cost(self, context: ExecutionContext, *, amount: float) -> None:
        """Record a cost value when a provider supplies one."""


class LoggingDecisionMetricsCollector:
    """Emit decision metrics as structured logs without external metric services.

    This implementation is deliberately lightweight. It does not aggregate,
    retain, or export metrics; a future adapter may implement the same protocol.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the collector with an injected or module logger."""
        self._logger = logger or get_logger(__name__)

    def record_provider_latency(
        self, context: ExecutionContext, *, model: str, duration_ms: float
    ) -> None:
        """Log one provider-latency measurement."""
        self._record(
            context,
            "decision_metric_provider_latency",
            model=model,
            duration_ms=duration_ms,
        )

    def record_retry(self, context: ExecutionContext, *, retry_count: int) -> None:
        """Log one retry-count measurement."""
        self._record(context, "decision_metric_retry", retry_count=retry_count)

    def record_timeout(self, context: ExecutionContext) -> None:
        """Log one provider timeout measurement."""
        self._record(context, "decision_metric_timeout")

    def record_success(self, context: ExecutionContext, *, model: str) -> None:
        """Log one provider success measurement."""
        self._record(context, "decision_metric_success", model=model)

    def record_failure(self, context: ExecutionContext, *, failure_type: str) -> None:
        """Log one provider failure measurement."""
        self._record(context, "decision_metric_failure", failure_type=failure_type)

    def record_fallback(self, context: ExecutionContext) -> None:
        """Log one deterministic fallback measurement."""
        self._record(context, "decision_metric_fallback", fallback_used=True)

    def record_tokens(self, context: ExecutionContext, *, token_count: int) -> None:
        """Log one token-usage measurement."""
        self._record(context, "decision_metric_tokens", token_count=token_count)

    def record_cost(self, context: ExecutionContext, *, amount: float) -> None:
        """Log one cost measurement when supplied by a provider."""
        self._record(context, "decision_metric_cost", amount=amount)

    def _record(self, context: ExecutionContext, event: str, **fields: object) -> None:
        """Emit one safe metric event through the common logging boundary."""
        log_event(self._logger, logging.INFO, event, context, **fields)
