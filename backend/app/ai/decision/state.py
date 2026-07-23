"""Lifecycle state definitions for one decision execution."""

from enum import Enum


class DecisionState(str, Enum):
    """Represent the lifecycle of one decision request."""

    RECEIVED = "received"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"

