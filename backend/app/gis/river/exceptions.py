"""Domain-specific failures for river-network dataset access."""

from backend.app.gis.exceptions import GISException


class RiverNetworkError(GISException):
    """Raised when an authoritative river-network dataset cannot be used safely."""
