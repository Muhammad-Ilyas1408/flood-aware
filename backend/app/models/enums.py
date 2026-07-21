"""Shared domain enumerations for Flood-Aware contracts."""

from enum import Enum


class ResponseStatus(str, Enum):
    """Describe the high-level outcome of an API response."""

    SUCCESS = "success"
    ERROR = "error"


class RiskLevel(str, Enum):
    """Classify the assessed flood risk level."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


class FloodSeverity(str, Enum):
    """Classify the severity of a flood event."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    EXTREME = "extreme"


class FloodStatus(str, Enum):
    """Describe the current operational state of flooding."""

    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    EMERGENCY = "emergency"


class Language(str, Enum):
    """Represent supported application languages."""

    ENGLISH = "en"
    URDU = "ur"


class DocumentType(str, Enum):
    """Classify knowledge documents handled by future retrieval modules."""

    GUIDELINE = "guideline"
    REPORT = "report"
    BULLETIN = "bulletin"
    POLICY = "policy"
