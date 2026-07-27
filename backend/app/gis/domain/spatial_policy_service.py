"""Production ownership of deterministic GIS analysis-window policy."""

from backend.app.gis.domain.exceptions import SpatialPolicyError
from backend.app.gis.domain.models import SpatialPolicy
from backend.app.gis.geometry import BoundingBox
from backend.app.models.flood import Coordinates


class SpatialPolicyService:
    """Produce a configured WGS84 analysis extent from canonical coordinates."""

    def __init__(self, policy: SpatialPolicy) -> None:
        """Initialize the sole injected spatial-analysis policy."""
        self._policy = policy

    def analysis_bounds(self, coordinates: Coordinates) -> BoundingBox:
        """Return one deterministic analysis window around a requested location."""
        if not isinstance(coordinates, Coordinates):
            raise SpatialPolicyError("Spatial policy requires Coordinates.")
        try:
            return BoundingBox(
                min_latitude=max(
                    -90.0, coordinates.latitude - self._policy.latitude_delta
                ),
                min_longitude=max(
                    -180.0, coordinates.longitude - self._policy.longitude_delta
                ),
                max_latitude=min(
                    90.0, coordinates.latitude + self._policy.latitude_delta
                ),
                max_longitude=min(
                    180.0, coordinates.longitude + self._policy.longitude_delta
                ),
            )
        except Exception as error:
            raise SpatialPolicyError(
                "Spatial analysis bounds could not be created."
            ) from error
