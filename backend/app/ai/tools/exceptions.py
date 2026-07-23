"""Domain exceptions for the framework-independent AI runtime."""


class AIRuntimeError(RuntimeError):
    """Base exception for AI runtime failures."""


class ToolRegistrationError(AIRuntimeError):
    """Raised when a tool cannot be registered safely."""


class ToolNotFoundError(AIRuntimeError):
    """Raised when a requested runtime tool is unavailable."""


class ToolExecutionError(AIRuntimeError):
    """Raised when a registered tool fails during execution."""


class PlanningError(AIRuntimeError):
    """Raised when a planner cannot provide a valid next tool."""


class RuntimeTimeoutError(AIRuntimeError):
    """Reserved for future runtime timeout enforcement."""

