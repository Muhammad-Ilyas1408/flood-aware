"""Lifecycle states for framework-independent runtime execution."""

from enum import Enum


class ToolStatus(str, Enum):
    """Describe the observable status of one runtime tool execution."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
