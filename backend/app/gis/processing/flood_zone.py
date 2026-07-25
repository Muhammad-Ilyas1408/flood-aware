"""Deterministic severity-buffer flood-zone generation."""

from time import perf_counter

from pyproj import CRS as PyprojCRS
from shapely.geometry.base import BaseGeometry

from backend.app.core.logger import get_logger
from backend.app.gis.config import FLOOD_BUFFER_METERS, GIS_CONFIG
from backend.app.gis.processing._spatial import local_metric_crs, transform_geometry
from backend.app.gis.processing.exceptions import FloodZoneError
from backend.app.gis.processing.models import FloodZone
from backend.app.models.enums import FloodSeverity

_LOGGER = get_logger(__name__)
_SUPPORTED_RIVER_GEOMETRY_TYPES = frozenset(
    {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}
)


class FloodZoneGenerator:
    """Create deterministic river-buffer flood zones from supplied severity inputs."""

    def generate(
        self,
        severity: FloodSeverity,
        river_geometry: BaseGeometry | None = None,
        river_crs: str | None = None,
    ) -> FloodZone:
        """Buffer a supplied river geometry using the configured severity mapping.

        Args:
            severity: Already-determined flood severity; no risk interpretation occurs here.
            river_geometry: Authoritative river geometry to buffer.
            river_crs: CRS of the supplied river geometry.

        Returns:
            Flood polygon expressed in the source river CRS.

        Raises:
            FloodZoneError: If input geometry, CRS, or generated polygon is invalid.
        """

        if not isinstance(severity, FloodSeverity):
            raise FloodZoneError("Flood zone generation requires a FloodSeverity.")
        started_at = perf_counter()
        _LOGGER.debug("Flood zone generation started: severity=%s", severity.value)
        river_geometry, river_crs = self._resolve_river_geometry(
            river_geometry, river_crs
        )
        try:
            source_crs = PyprojCRS.from_user_input(river_crs).to_string()
            metric_crs = local_metric_crs(river_geometry, source_crs)
            buffer_meters = FLOOD_BUFFER_METERS[severity]
            metric_geometry = transform_geometry(river_geometry, source_crs, metric_crs)
            polygon = transform_geometry(
                metric_geometry.buffer(buffer_meters),
                metric_crs,
                source_crs,
            )
        except Exception as error:
            raise FloodZoneError(
                "Flood zone generation failed for the supplied river geometry."
            ) from error
        if polygon.is_empty or not polygon.is_valid:
            raise FloodZoneError("Generated flood zone polygon is invalid.")
        flood_zone = FloodZone(
            geometry=polygon,
            crs=source_crs,
            severity=severity,
            buffer_meters=buffer_meters,
        )
        _LOGGER.info(
            "Flood zone generated: severity=%s buffer_meters=%s crs=%s duration_ms=%.2f",
            severity.value,
            buffer_meters,
            source_crs,
            (perf_counter() - started_at) * 1000,
        )
        return flood_zone

    def _resolve_river_geometry(
        self,
        river_geometry: BaseGeometry | None,
        river_crs: str | None,
    ) -> tuple[BaseGeometry, str]:
        """Validate supplied river geometry inputs."""
        if not isinstance(river_geometry, BaseGeometry) or river_geometry.is_empty:
            raise FloodZoneError(
                "Flood zone generation requires a non-empty river geometry."
            )
        if river_geometry.geom_type not in _SUPPORTED_RIVER_GEOMETRY_TYPES:
            raise FloodZoneError(
                "River geometry type is unsupported for flood-zone buffering."
            )
        if not river_geometry.is_valid:
            raise FloodZoneError("River geometry must be valid.")
        if not isinstance(river_crs, str) or not river_crs.strip():
            raise FloodZoneError("River geometry CRS is required.")
        return river_geometry, river_crs
