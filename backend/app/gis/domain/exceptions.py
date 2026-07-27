"""Domain-service failures for GIS orchestration."""

from backend.app.gis.exceptions import GISException


class GISDomainServiceError(GISException):
    """Raised when composed GIS data acquisition or analysis cannot complete."""


class FloodClassificationError(GISException):
    """Raised when a forecast cannot be classified by the configured policy."""


class SpatialPolicyError(GISException):
    """Raised when configured spatial-analysis policy cannot produce an extent."""


class GISRequestFactoryError(GISException):
    """Raised when canonical GIS domain request assembly fails."""
