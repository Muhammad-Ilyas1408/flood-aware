"""Immutable river-network data contracts."""

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry

from backend.app.gis.river.exceptions import RiverNetworkError


@dataclass(frozen=True, slots=True)
class RiverGeometry:
    """Represent authoritative river geometry and its validated source CRS."""

    geometry: BaseGeometry
    crs: str

    def __post_init__(self) -> None:
        """Reject invalid geometry and CRS values at the data-access boundary."""
        if not isinstance(self.geometry, BaseGeometry) or self.geometry.is_empty:
            raise RiverNetworkError("River geometry must be non-empty.")
        if not self.geometry.is_valid:
            raise RiverNetworkError("River geometry must be valid.")
        if not isinstance(self.crs, str) or not self.crs.strip():
            raise RiverNetworkError("River geometry requires a valid CRS.")
