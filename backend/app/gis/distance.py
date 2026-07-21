"""Pure mathematical distance and bearing calculations for geographic points."""

from math import asin, atan2, cos, degrees, radians, sin, sqrt

from backend.app.gis.constants import EARTH_RADIUS_KILOMETERS, EARTH_RADIUS_METERS
from backend.app.gis.exceptions import GeometryError
from backend.app.gis.geometry import DistanceResult, Point
from backend.app.gis.validation import validate_coordinate_pair, validate_crs


def haversine_distance(origin: Point, destination: Point) -> DistanceResult:
    """Return the great-circle distance between two points using the Haversine formula.

    The formula computes ``2 * asin(sqrt(a))`` from latitude and longitude angular
    differences, then multiplies the result by the mean Earth radius.

    Raises:
        GeometryError: If either argument is not a valid Point model.
    """

    origin_latitude, origin_longitude = _validated_point_coordinates(origin)
    destination_latitude, destination_longitude = _validated_point_coordinates(destination)

    latitude_difference = radians(destination_latitude - origin_latitude)
    longitude_difference = radians(destination_longitude - origin_longitude)
    origin_latitude_radians = radians(origin_latitude)
    destination_latitude_radians = radians(destination_latitude)

    haversine_value = (
        sin(latitude_difference / 2) ** 2
        + cos(origin_latitude_radians)
        * cos(destination_latitude_radians)
        * sin(longitude_difference / 2) ** 2
    )
    central_angle = 2 * asin(sqrt(haversine_value))
    return DistanceResult(
        meters=EARTH_RADIUS_METERS * central_angle,
        kilometers=EARTH_RADIUS_KILOMETERS * central_angle,
    )


def distance_meters(origin: Point, destination: Point) -> float:
    """Return the Haversine distance between two points in meters."""

    return haversine_distance(origin, destination).meters


def distance_kilometers(origin: Point, destination: Point) -> float:
    """Return the Haversine distance between two points in kilometers."""

    return haversine_distance(origin, destination).kilometers


def bearing(origin: Point, destination: Point) -> float:
    """Return the initial compass bearing from origin to destination in degrees.

    The returned bearing is normalized to the inclusive range from 0 to less than 360.

    Raises:
        GeometryError: If either argument is not a valid Point model.
    """

    origin_latitude, origin_longitude = _validated_point_coordinates(origin)
    destination_latitude, destination_longitude = _validated_point_coordinates(destination)
    longitude_difference = radians(destination_longitude - origin_longitude)
    origin_latitude_radians = radians(origin_latitude)
    destination_latitude_radians = radians(destination_latitude)

    bearing_radians = atan2(
        sin(longitude_difference) * cos(destination_latitude_radians),
        cos(origin_latitude_radians) * sin(destination_latitude_radians)
        - sin(origin_latitude_radians)
        * cos(destination_latitude_radians)
        * cos(longitude_difference),
    )
    return degrees(bearing_radians) % 360


def _validated_point_coordinates(point: Point) -> tuple[float, float]:
    """Return validated coordinates for a Point used in a spatial calculation."""

    if not isinstance(point, Point):
        raise GeometryError("Spatial calculations require Point models.")
    validate_crs(point.crs)
    return validate_coordinate_pair(point.latitude, point.longitude)
