"""Immutable configured policy for deterministic flood classification."""

from dataclasses import dataclass

from backend.app.config.settings import Settings


@dataclass(frozen=True, slots=True)
class FloodClassificationPolicy:
    """Store operational discharge thresholds in cubic metres per second."""

    moderate_discharge: float
    major_discharge: float
    extreme_discharge: float

    @classmethod
    def from_settings(cls, settings: Settings) -> "FloodClassificationPolicy":
        """Create the policy from the existing validated application settings."""
        return cls(
            moderate_discharge=settings.flood_moderate_discharge,
            major_discharge=settings.flood_major_discharge,
            extreme_discharge=settings.flood_extreme_discharge,
        )

    def __post_init__(self) -> None:
        """Require strictly increasing non-negative operational thresholds."""
        thresholds = (
            self.moderate_discharge,
            self.major_discharge,
            self.extreme_discharge,
        )
        if any(isinstance(value, bool) or value < 0 for value in thresholds):
            raise ValueError("Flood classification thresholds must be non-negative.")
        if thresholds != tuple(sorted(thresholds)) or len(set(thresholds)) != 3:
            raise ValueError("Flood classification thresholds must strictly increase.")
