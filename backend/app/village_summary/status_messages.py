"""Deterministic status-message mapping from flood severity to a short label.

This mapping is intentionally static and non-generative: it lets the
lightweight village summary endpoint present an honest, consistent status
without invoking the LangGraph decision agent or OpenAI, unlike
``/conversation``.
"""

from backend.app.models.enums import FloodSeverity

INSUFFICIENT_DATA_STATUS_MESSAGE = "Insufficient data to assess flood risk"

_STATUS_MESSAGES: dict[FloodSeverity, str] = {
    FloodSeverity.MINOR: "Monitor conditions",
    FloodSeverity.MODERATE: "Stay alert, monitor forecasts",
    FloodSeverity.MAJOR: "Consider evacuation preparations",
    FloodSeverity.EXTREME: "Consider evacuation preparations",
}


def status_message_for(severity: FloodSeverity | None) -> str:
    """Return the deterministic status message mapped from a severity tier.

    Args:
        severity: The classified flood severity, or ``None`` when severity
            could not be honestly determined.
    """
    if severity is None:
        return INSUFFICIENT_DATA_STATUS_MESSAGE
    return _STATUS_MESSAGES[severity]
