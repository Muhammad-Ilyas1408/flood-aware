"""Reusable validation utilities for shared backend contracts."""

import re
from datetime import date

from backend.app.core.validation_exceptions import (
    CoordinateValidationError,
    DateRangeValidationError,
    IdentifierValidationError,
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    """Validate and return a geographic coordinate pair.

    Raises:
        CoordinateValidationError: If latitude or longitude is outside its WGS 84 range.
    """

    if not -90 <= latitude <= 90:
        raise CoordinateValidationError(
            "Latitude must be between -90 and 90 degrees.",
            field="latitude",
            value=latitude,
        )
    if not -180 <= longitude <= 180:
        raise CoordinateValidationError(
            "Longitude must be between -180 and 180 degrees.",
            field="longitude",
            value=longitude,
        )
    return latitude, longitude


def validate_date_range(start_date: date, end_date: date) -> tuple[date, date]:
    """Validate and return an inclusive date range.

    Raises:
        DateRangeValidationError: If the end date is earlier than the start date.
    """

    if end_date < start_date:
        raise DateRangeValidationError(
            "End date must not be earlier than start date.",
            field="end_date",
            value=end_date,
        )
    return start_date, end_date


def validate_identifier(identifier: str) -> str:
    """Validate and return a stable identifier safe for shared contracts.

    Raises:
        IdentifierValidationError: If the identifier does not match the supported format.
    """

    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise IdentifierValidationError(
            "Identifier must start with an alphanumeric character and contain only "
            "letters, numbers, periods, underscores, colons, or hyphens.",
            field="identifier",
            value=identifier,
        )
    return identifier
