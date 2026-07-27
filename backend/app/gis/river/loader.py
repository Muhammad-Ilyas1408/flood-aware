"""Lazy, cached retrieval of authoritative OSM waterway geometry."""

from pathlib import Path
from time import perf_counter

import geopandas as gpd
from pyproj import CRS
from shapely.ops import unary_union

from backend.app.core.logger import get_logger
from backend.app.gis.config import GIS_CONFIG
from backend.app.gis.geometry import BoundingBox
from backend.app.gis.river.exceptions import RiverNetworkError
from backend.app.gis.river.models import RiverGeometry

_LOGGER = get_logger(__name__)
_WATERWAY_COLUMN = "waterway"


class RiverNetworkLoader:
    """Provide bounded, deterministic river geometry from an OSM PBF dataset.

    GeoPandas closes the underlying file after each read. This loader therefore
    owns and caches immutable query results rather than retaining file handles.
    Call ``close`` to release those in-memory results at its composition boundary.
    """

    def __init__(self, dataset_path: Path) -> None:
        """Initialize the loader for one authoritative local OSM PBF dataset."""
        self._dataset_path = Path(dataset_path)
        self._geometry_cache: dict[
            tuple[float, float, float, float] | None, RiverGeometry
        ] = {}

    def get_geometry(self, bounds: BoundingBox | None = None) -> RiverGeometry:
        """Return cached or newly loaded waterway geometry for an optional extent.

        Args:
            bounds: Optional WGS84 query extent. ``None`` requests the full dataset.

        Returns:
            Authoritative OSM waterway geometry and its source CRS.

        Raises:
            RiverNetworkError: If the dataset, bounds, CRS, or waterway features are
                invalid or unavailable.
        """
        cache_key = self._cache_key(bounds)
        cached = self._geometry_cache.get(cache_key)
        if cached is not None:
            return cached
        self._validate_dataset()
        started_at = perf_counter()
        _LOGGER.info("River network loading started: dataset=%s", self._dataset_path)
        try:
            layer = gpd.read_file(
                self._dataset_path,
                layer="lines",
                bbox=cache_key,
            )
            river_geometry = self._to_river_geometry(layer)
        except RiverNetworkError:
            raise
        except Exception as error:
            raise RiverNetworkError(
                "River network dataset could not be loaded."
            ) from error
        self._geometry_cache[cache_key] = river_geometry
        _LOGGER.info(
            "River network loaded: dataset=%s crs=%s duration_ms=%.2f",
            self._dataset_path,
            river_geometry.crs,
            (perf_counter() - started_at) * 1000,
        )
        return river_geometry

    def close(self) -> None:
        """Release cached in-memory query results owned by this loader."""
        self._geometry_cache.clear()

    def _validate_dataset(self) -> None:
        """Validate the configured production OSM PBF source before reading it."""
        if (
            not self._dataset_path.is_file()
            or tuple(self._dataset_path.suffixes[-2:]) != GIS_CONFIG.osm_pbf_suffixes
        ):
            raise RiverNetworkError(
                "River network loader requires an existing .osm.pbf dataset."
            )

    @staticmethod
    def _cache_key(
        bounds: BoundingBox | None,
    ) -> tuple[float, float, float, float] | None:
        """Convert an immutable bounding box to GeoPandas' x/y order."""
        if bounds is None:
            return None
        if not isinstance(bounds, BoundingBox):
            raise RiverNetworkError("River-network bounds must be a GIS BoundingBox.")
        return (
            bounds.min_longitude,
            bounds.min_latitude,
            bounds.max_longitude,
            bounds.max_latitude,
        )

    @staticmethod
    def _to_river_geometry(layer: gpd.GeoDataFrame) -> RiverGeometry:
        """Extract OSM waterway features without modifying their geometry."""
        if not isinstance(layer, gpd.GeoDataFrame) or layer.crs is None:
            raise RiverNetworkError("River network requires a GeoDataFrame with a CRS.")
        if _WATERWAY_COLUMN not in layer.columns:
            raise RiverNetworkError("River network dataset has no waterway features.")
        waterways = layer.loc[
            layer[_WATERWAY_COLUMN].fillna("").astype(str).str.strip().ne("")
        ]
        if waterways.empty:
            raise RiverNetworkError(
                "River network query returned no waterway features."
            )
        geometry = unary_union(tuple(waterways.geometry))
        crs = CRS.from_user_input(layer.crs).to_string()
        return RiverGeometry(geometry=geometry, crs=crs)
