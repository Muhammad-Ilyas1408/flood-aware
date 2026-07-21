"""Reusable pure-Python geometry helper functions."""

from math import atan2, cos, degrees, radians, sin, sqrt

from backend.app.gis.constants import (
    DEFAULT_COORDINATE_PRECISION,
    MAX_LONGITUDE,
    MIN_LONGITUDE,
)
from backend.app.gis.exceptions import CoordinateError, GeometryError
from backend.app.gis.geometry import BoundingBox, Point
from backend.app.gis.validation import validate_coordinate_pair, validate_longitude


def midpoint(origin: Point, destination: Point) -> Point:
    """Return the geographic midpoint of two points on a spherical Earth."""

    origin_latitude, origin_longitude = _validated_point_coordinates(origin)
    destination_latitude, destination_longitude = _validated_point_coordinates(destination)
    origin_latitude_radians = radians(origin_latitude)
    origin_longitude_radians = radians(origin_longitude)
    destination_latitude_radians = radians(destination_latitude)
    longitude_difference = radians(destination_longitude - origin_longitude)

    horizontal_x = cos(destination_latitude_radians) * cos(longitude_difference)
    horizontal_y = cos(destination_latitude_radians) * sin(longitude_difference)
    midpoint_latitude = atan2(
        sin(origin_latitude_radians) + sin(destination_latitude_radians),
        sqrt((cos(origin_latitude_radians) + horizontal_x) ** 2 + horizontal_y**2),
    )
    midpoint_longitude = origin_longitude_radians + atan2(
        horizontal_y,
        cos(origin_latitude_radians) + horizontal_x,
    )
    return Point(
        latitude=degrees(midpoint_latitude),
        longitude=normalize_longitude(degrees(midpoint_longitude)),
        crs=origin.crs,
    )


def bounding_box_from_points(points: list[Point]) -> BoundingBox:
    """Return the smallest latitude-longitude bounding box containing all points.

    Raises:
        GeometryError: If no points are provided.
    """

    if not points:
        raise GeometryError("Cannot create a bounding box from an empty point list.")

    return BoundingBox(
        min_latitude=min(point.latitude for point in points),
        min_longitude=min(point.longitude for point in points),
        max_latitude=max(point.latitude for point in points),
        max_longitude=max(point.longitude for point in points),
    )


def bounding_box_center(bounding_box: BoundingBox) -> Point:
    """Return the arithmetic center of a bounding box."""

    return bounding_box.center()


def normalize_longitude(longitude: float) -> float:
    """Normalize a finite numeric longitude into the inclusive range [-180, 180].

    Raises:
        CoordinateError: If longitude is not a finite numeric value.
    """

    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
        raise CoordinateError("Longitude must be a numeric value.")

    normalized_longitude = (float(longitude) - MIN_LONGITUDE) % (
        MAX_LONGITUDE - MIN_LONGITUDE
    ) + MIN_LONGITUDE
    if normalized_longitude == MIN_LONGITUDE and longitude > 0:
        normalized_longitude = MAX_LONGITUDE
    return validate_longitude(normalized_longitude)


def round_coordinates(point: Point) -> Point:
    """Return a point rounded to the configured coordinate precision."""

    return Point(
        latitude=round(point.latitude, DEFAULT_COORDINATE_PRECISION),
        longitude=round(point.longitude, DEFAULT_COORDINATE_PRECISION),
        crs=point.crs,
    )


def _validated_point_coordinates(point: Point) -> tuple[float, float]:
    """Return validated coordinates for a Point used in a geometry helper."""

    if not isinstance(point, Point):
        raise GeometryError("Geometry helpers require Point models.")
    return validate_coordinate_pair(point.latitude, point.longitude)
