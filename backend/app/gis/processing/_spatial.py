"""Private CRS transformation helpers shared by GIS-processing components."""

from math import floor

from pyproj import CRS as PyprojCRS
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from backend.app.gis.config import GIS_CONFIG


def transform_geometry(
    geometry: BaseGeometry,
    source_crs: str,
    target_crs: str,
) -> BaseGeometry:
    """Reproject one Shapely geometry without changing its topology intentionally."""

    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(transformer.transform, geometry)


def local_metric_crs(geometry: BaseGeometry, source_crs: str) -> str:
    """Return the centroid-derived WGS84 UTM CRS appropriate for metric operations."""

    wgs84_geometry = transform_geometry(geometry, source_crs, GIS_CONFIG.default_crs)
    centroid = wgs84_geometry.centroid
    zone = (
        floor(
            (centroid.x + GIS_CONFIG.longitude_offset_degrees)
            / GIS_CONFIG.utm_zone_width_degrees
        )
        + GIS_CONFIG.minimum_utm_zone
    )
    if not GIS_CONFIG.minimum_utm_zone <= zone <= GIS_CONFIG.maximum_utm_zone:
        raise ValueError("Geometry centroid cannot be mapped to a supported UTM zone.")
    epsg = (
        GIS_CONFIG.northern_utm_epsg_base
        if centroid.y >= 0
        else GIS_CONFIG.southern_utm_epsg_base
    ) + zone
    return PyprojCRS.from_epsg(epsg).to_string()


def geometry_area_square_meters(geometry: BaseGeometry, crs: str) -> float:
    """Return geometry area in square meters using its centroid-derived UTM CRS."""

    metric_crs = local_metric_crs(geometry, crs)
    return float(transform_geometry(geometry, crs, metric_crs).area)
