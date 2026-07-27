"""GIS-specific exception hierarchy for Flood-Aware."""


class GISException(Exception):
    """Base exception for GIS foundation failures."""


class GISAnalysisError(GISException):
    """Raised when the production GIS analysis orchestration cannot complete."""


class CRSError(GISException):
    """Raised when a coordinate reference system is invalid or unsupported."""


class CoordinateError(GISException):
    """Raised when geographic coordinate values are invalid."""


class GeometryError(GISException):
    """Raised when geometric data is invalid in future geometry operations."""


class GeoJSONError(GeometryError):
    """Raised when GeoJSON data is invalid in future GeoJSON operations."""
