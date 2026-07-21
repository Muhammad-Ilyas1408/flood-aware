"""Lightweight coordinate reference system representations and lookup helpers."""

from enum import IntEnum

from backend.app.gis.constants import WGS84_EPSG, WGS84_NAME
from backend.app.gis.exceptions import CRSError


class CRS(IntEnum):
    """Represent coordinate reference systems supported by the GIS foundation."""

    WGS84 = WGS84_EPSG

    @property
    def epsg_code(self) -> int:
        """Return the integer EPSG code for this coordinate reference system."""

        return int(self)

    @property
    def display_name(self) -> str:
        """Return a human-readable name for this coordinate reference system."""

        match self:
            case CRS.WGS84:
                return WGS84_NAME
            case _:
                raise CRSError(f"Unsupported CRS EPSG:{self.epsg_code}.")


def get_crs_by_epsg(epsg_code: int) -> CRS:
    """Return the supported CRS for an EPSG code.

    Raises:
        CRSError: If the EPSG code is not an integer supported by the application.
    """

    if isinstance(epsg_code, bool) or not isinstance(epsg_code, int):
        raise CRSError("EPSG code must be an integer.")

    try:
        return CRS(epsg_code)
    except ValueError as error:
        raise CRSError(f"Unsupported CRS EPSG:{epsg_code}.") from error
