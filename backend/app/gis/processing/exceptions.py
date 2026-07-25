"""Exception hierarchy for GIS data-processing components."""

from backend.app.gis.exceptions import GISException


class GISProcessingError(GISException):
    """Base exception for local GIS data-processing failures."""


class DEMError(GISProcessingError):
    """Raised when a DEM cannot be validated or queried safely."""


class FloodZoneError(GISProcessingError):
    """Raised when a deterministic flood zone cannot be generated."""


class WorldPopError(GISProcessingError):
    """Raised when a WorldPop raster cannot be loaded or masked safely."""


class PopulationExposureError(GISProcessingError):
    """Raised when population exposure cannot be calculated safely."""


class OSMError(GISProcessingError):
    """Raised when OpenStreetMap infrastructure data cannot be loaded safely."""


class InfrastructureImpactError(GISProcessingError):
    """Raised when infrastructure impact cannot be calculated safely."""


class FloodEvidenceError(GISProcessingError):
    """Raised when GIS outputs cannot form validated AI-ready flood evidence."""
