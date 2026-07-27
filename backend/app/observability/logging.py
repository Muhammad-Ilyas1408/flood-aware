"""Safe structured logging helpers for correlated operational events."""

import logging
from typing import Any

from backend.app.observability.context import ExecutionContext


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    context: ExecutionContext,
    **fields: Any,
) -> None:
    """Emit one structured event without serializing operational payloads.

    Callers supply only safe metadata such as durations, attempts, node names,
    and failure classifications. Prompts, evidence, user input, and model output
    are intentionally excluded from this boundary.
    """
    logger.log(level, event, extra={**context.log_fields(), **fields})
