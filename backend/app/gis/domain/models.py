"""Immutable public inputs for GIS domain-service execution."""

from dataclasses import dataclass

from backend.app.forecast.models import ForecastResult
from backend.app.gis.geometry import BoundingBox
from backend.app.models.enums import FloodSeverity
from backend.app.models.flood import Coordinates


@dataclass(frozen=True, slots=True)
class GISDomainRequest:
    """Collect the minimum caller-supplied facts for one GIS analysis execution.

    Flood severity remains an upstream factual input. The request intentionally
    does not expose internal river geometry or infrastructure layer objects.
    """

    context: "PreparedFloodContext"

    def __post_init__(self) -> None:
        """Validate public request types without duplicating component validation."""
        if not isinstance(self.context, PreparedFloodContext):
            raise ValueError("GIS domain execution requires a PreparedFloodContext.")


@dataclass(frozen=True, slots=True)
class PreparedFloodContext:
    """Represent canonical flood facts prepared for GIS execution."""

    forecast: ForecastResult
    severity: FloodSeverity
    bounds: BoundingBox
    coordinates: Coordinates

    def __post_init__(self) -> None:
        """Validate canonical domain inputs without performing preparation logic."""
        if not isinstance(self.forecast, ForecastResult):
            raise ValueError("Prepared flood context requires a ForecastResult.")
        if not isinstance(self.severity, FloodSeverity):
            raise ValueError("Prepared flood context requires a FloodSeverity.")
        if not isinstance(self.bounds, BoundingBox):
            raise ValueError("Prepared flood context requires a GIS BoundingBox.")
        if not isinstance(self.coordinates, Coordinates):
            raise ValueError("Prepared flood context requires Coordinates.")


@dataclass(frozen=True, slots=True)
class SpatialPolicy:
    """Configure the WGS84 analysis extent around a requested coordinate."""

    latitude_delta: float = 0.1
    longitude_delta: float = 0.1

    def __post_init__(self) -> None:
        """Require positive bounded coordinate deltas for one analysis window."""
        values = (self.latitude_delta, self.longitude_delta)
        if any(isinstance(value, bool) or not 0 < value <= 90 for value in values):
            raise ValueError("Spatial policy deltas must be between 0 and 90 degrees.")
