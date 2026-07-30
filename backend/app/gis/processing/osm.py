"""OpenStreetMap infrastructure extraction isolated behind GeoPandas."""

from pathlib import Path
from time import perf_counter

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from backend.app.core.logger import get_logger
from backend.app.gis.config import GIS_CONFIG, OSM_AMENITY_TAGS
from backend.app.gis.geometry import BoundingBox
from backend.app.gis.processing.exceptions import OSMError
from backend.app.gis.processing.models import InfrastructureLayers

_LOGGER = get_logger(__name__)


class OSMLoader:
    """Extract selected infrastructure layers from a local OpenStreetMap PBF file.

    The full-extent dataset is parsed from disk exactly once (either eagerly
    via ``warm_up`` or lazily on first use) and retained in memory; every
    requested extent is served by spatially filtering those already-parsed
    layers rather than re-reading the PBF source.
    """

    def __init__(self, path: Path) -> None:
        """Initialize the loader for one configured OSM PBF source.

        Args:
            path: Path to the downloaded ``.osm.pbf`` data source.
        """

        self._path = path
        self._full_extent_layers: (
            tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame] | None
        ) = None

    def warm_up(self) -> None:
        """Eagerly parse the full dataset once, ahead of any request.

        Intended to be called once at application startup so the expensive
        PBF parse is paid a single time rather than on every request.

        Raises:
            OSMError: If the source is absent, unsupported, or cannot be read.
        """
        self._validate_source()
        self._load_full_extent_layers()

    def close(self) -> None:
        """Release the in-memory full-extent layers owned by this loader."""
        self._full_extent_layers = None

    def load(self, bounds: BoundingBox | None = None) -> InfrastructureLayers:
        """Load roads and critical public-service assets from the PBF source.

        Args:
            bounds: Optional WGS84 extent used to limit the returned features.

        Returns:
            GeoDataFrames for infrastructure categories with source CRS preserved.

        Raises:
            OSMError: If the source is absent, unsupported, or cannot be read.
        """

        self._validate_source()
        if bounds is not None and not isinstance(bounds, BoundingBox):
            raise OSMError("OSM bounds must be a GIS BoundingBox.")
        started_at = perf_counter()
        lines, points, polygons = self._clipped_layers(bounds)

        facilities = _combine_layers(points, polygons)
        infrastructure_layers = InfrastructureLayers(
            roads=_filter_nonblank(lines, "highway"),
            bridges=_filter_bridge(lines),
            schools=_filter_amenity(facilities, OSM_AMENITY_TAGS["schools"]),
            hospitals=_filter_amenity(facilities, OSM_AMENITY_TAGS["hospitals"]),
            clinics=_filter_amenity(facilities, OSM_AMENITY_TAGS["clinics"]),
            police_stations=_filter_amenity(
                facilities,
                OSM_AMENITY_TAGS["police_stations"],
            ),
            fire_stations=_filter_amenity(
                facilities,
                OSM_AMENITY_TAGS["fire_stations"],
            ),
        )
        _LOGGER.info(
            "OSM infrastructure layers loaded: path=%s roads=%s critical_assets=%s crs=%s duration_ms=%.2f",
            self._path,
            len(infrastructure_layers.roads),
            sum(
                len(layer)
                for layer in (
                    infrastructure_layers.hospitals,
                    infrastructure_layers.clinics,
                    infrastructure_layers.police_stations,
                    infrastructure_layers.fire_stations,
                )
            ),
            infrastructure_layers.roads.crs,
            (perf_counter() - started_at) * 1000,
        )
        return infrastructure_layers

    def _validate_source(self) -> None:
        """Validate the configured production OSM PBF source before reading it."""
        if (
            not self._path.is_file()
            or tuple(self._path.suffixes[-2:]) != GIS_CONFIG.osm_pbf_suffixes
        ):
            raise OSMError("OSM loader requires an existing .osm.pbf file.")

    def _load_full_extent_layers(
        self,
    ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Parse the full dataset from disk exactly once and retain it in memory."""
        if self._full_extent_layers is None:
            started_at = perf_counter()
            _LOGGER.info("OSM full-extent parse started: path=%s", self._path)
            try:
                lines = gpd.read_file(self._path, layer="lines")
                points = gpd.read_file(self._path, layer="points")
                polygons = gpd.read_file(self._path, layer="multipolygons")
            except Exception as error:
                raise OSMError(
                    "OpenStreetMap infrastructure data could not be loaded."
                ) from error
            self._full_extent_layers = (lines, points, polygons)
            _LOGGER.info(
                "OSM full-extent parse finished: path=%s duration_ms=%.2f",
                self._path,
                (perf_counter() - started_at) * 1000,
            )
        return self._full_extent_layers

    def _clipped_layers(
        self, bounds: BoundingBox | None
    ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Return the in-memory full-extent layers filtered to one requested bbox."""
        lines, points, polygons = self._load_full_extent_layers()
        bbox = _bbox_tuple(bounds)
        if bbox is None:
            return lines, points, polygons
        bbox_polygon = box(*bbox)
        return (
            lines.loc[lines.geometry.intersects(bbox_polygon)],
            points.loc[points.geometry.intersects(bbox_polygon)],
            polygons.loc[polygons.geometry.intersects(bbox_polygon)],
        )


def _bbox_tuple(bounds: BoundingBox | None) -> tuple[float, float, float, float] | None:
    """Convert an immutable GIS bounding box to GeoPandas' x/y bbox ordering."""

    if bounds is None:
        return None
    return (
        bounds.min_longitude,
        bounds.min_latitude,
        bounds.max_longitude,
        bounds.max_latitude,
    )


def _combine_layers(
    first: gpd.GeoDataFrame, second: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Combine two same-CRS facility layers into one GeoDataFrame."""

    if first.empty:
        return second.copy()
    if second.empty:
        return first.copy()
    return gpd.GeoDataFrame(
        pd.concat((first, second), ignore_index=True),
        geometry="geometry",
        crs=first.crs,
    )


def _filter_nonblank(layer: gpd.GeoDataFrame, column: str) -> gpd.GeoDataFrame:
    """Return rows whose selected OSM tag has a nonblank value."""

    if column not in layer.columns:
        return layer.iloc[0:0].copy()
    values = layer[column].fillna("").astype(str).str.strip()
    return layer.loc[values.ne("")].copy()


def _filter_bridge(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return OSM bridge features, excluding explicit false-like tag values."""

    bridges = _filter_nonblank(layer, "bridge")
    if bridges.empty:
        return bridges
    values = bridges["bridge"].astype(str).str.lower()
    return bridges.loc[~values.isin(GIS_CONFIG.bridge_false_values)].copy()


def _filter_amenity(layer: gpd.GeoDataFrame, amenity: str) -> gpd.GeoDataFrame:
    """Return features matching one required OSM amenity value."""

    if "amenity" not in layer.columns:
        return layer.iloc[0:0].copy()
    values = layer["amenity"].fillna("").astype(str).str.lower()
    return layer.loc[values.eq(amenity)].copy()
