"""Immutable constants shared by Flood-Aware GIS foundation modules."""

from typing import Final

WGS84_EPSG: Final[int] = 4326
WGS84_NAME: Final[str] = "WGS 84"

MIN_LATITUDE: Final[float] = -90.0
MAX_LATITUDE: Final[float] = 90.0
MIN_LONGITUDE: Final[float] = -180.0
MAX_LONGITUDE: Final[float] = 180.0

EARTH_RADIUS_METERS: Final[float] = 6_371_008.8
EARTH_RADIUS_KILOMETERS: Final[float] = 6_371.0088
DEFAULT_COORDINATE_PRECISION: Final[int] = 6
