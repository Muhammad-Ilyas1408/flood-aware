"""Structural provider contracts for genuinely replaceable GIS data sources."""

from typing import Protocol

from backend.app.forecast.models import ForecastResult
from backend.app.gis.geometry import BoundingBox
from backend.app.gis.processing.models import InfrastructureLayers
from backend.app.gis.river.models import RiverGeometry


class ForecastProvider(Protocol):
    """Provide a canonical forecast for one coordinate pair."""

    def get_forecast(self, latitude: float, longitude: float) -> ForecastResult:
        """Return the authoritative forecast result."""


class RiverProvider(Protocol):
    """Provide authoritative river geometry for one analysis extent."""

    def get_geometry(self, bounds: BoundingBox | None = None) -> RiverGeometry:
        """Return source geometry and CRS."""


class InfrastructureProvider(Protocol):
    """Provide infrastructure layers for one analysis extent."""

    def load(self, bounds: BoundingBox | None = None) -> InfrastructureLayers:
        """Return authoritative infrastructure layers."""
