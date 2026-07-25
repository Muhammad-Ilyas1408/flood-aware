"""Pure validation utilities for shared GIS foundation values."""

from math import isfinite

from backend.app.gis.constants import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
)
from backend.app.gis.crs import CRS, get_crs_by_epsg
from backend.app.gis.exceptions import CoordinateError, CRSError


def validate_latitude(latitude: float) -> float:
    """Validate and return a geographic latitude in decimal degrees.

    Raises:
        CoordinateError: If latitude is non-numeric, non-finite, or outside valid bounds.
    """

    return _validate_numeric_coordinate(
        latitude, MIN_LATITUDE, MAX_LATITUDE, "Latitude"
    )


def validate_longitude(longitude: float) -> float:
    """Validate and return a geographic longitude in decimal degrees.

    Raises:
        CoordinateError: If longitude is non-numeric, non-finite, or outside valid bounds.
    """

    return _validate_numeric_coordinate(
        longitude, MIN_LONGITUDE, MAX_LONGITUDE, "Longitude"
    )


def validate_coordinate_pair(latitude: float, longitude: float) -> tuple[float, float]:
    """Validate and return a latitude-longitude coordinate pair.

    Raises:
        CoordinateError: If either coordinate is invalid.
    """

    return validate_latitude(latitude), validate_longitude(longitude)


def validate_epsg(epsg_code: int) -> int:
    """Validate and return a supported EPSG code.

    Raises:
        CRSError: If the EPSG code is invalid or unsupported.
    """

    return get_crs_by_epsg(epsg_code).epsg_code


def validate_crs(crs: CRS | int) -> CRS:
    """Validate and return a supported CRS representation.

    Raises:
        CRSError: If the CRS value is invalid or unsupported.
    """

    if isinstance(crs, CRS):
        return crs
    return get_crs_by_epsg(crs)


def _validate_numeric_coordinate(
    value: float,
    minimum: float,
    maximum: float,
    coordinate_name: str,
) -> float:
    """Validate a bounded finite coordinate value."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CoordinateError(f"{coordinate_name} must be a numeric value.")

    numeric_value = float(value)
    if not isfinite(numeric_value) or not minimum <= numeric_value <= maximum:
        raise CoordinateError(
            f"{coordinate_name} must be between {minimum} and {maximum} degrees."
        )
    return numeric_value
