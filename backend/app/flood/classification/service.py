"""Single production owner of deterministic forecast severity classification."""

from backend.app.forecast.models import ForecastResult
from backend.app.flood.classification.exceptions import FloodClassificationError
from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.models.enums import FloodSeverity


class FloodClassificationService:
    """Classify canonical forecasts through one injected operational policy."""

    def __init__(self, policy: FloodClassificationPolicy) -> None:
        """Initialize the service with its immutable threshold policy."""
        self._policy = policy

    def classify(self, forecast: ForecastResult) -> FloodSeverity:
        """Return severity from the maximum forecast discharge value."""
        if not isinstance(forecast, ForecastResult):
            raise FloodClassificationError(
                "Flood classification requires a ForecastResult."
            )
        try:
            maximum_discharge = max(
                point.discharge_m3_per_second for point in forecast.series.points
            )
        except Exception as error:
            raise FloodClassificationError("Flood classification failed.") from error
        if maximum_discharge >= self._policy.extreme_discharge:
            return FloodSeverity.EXTREME
        if maximum_discharge >= self._policy.major_discharge:
            return FloodSeverity.MAJOR
        if maximum_discharge >= self._policy.moderate_discharge:
            return FloodSeverity.MODERATE
        return FloodSeverity.MINOR
