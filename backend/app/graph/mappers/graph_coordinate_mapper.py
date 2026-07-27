"""Map immutable graph coordinates into canonical domain coordinates."""

from backend.app.graph.state import Coordinate
from backend.app.models.flood import Coordinates


class GraphCoordinateMapper:
    """Translate graph-owned coordinates for domain-service consumption."""

    @staticmethod
    def to_domain(coordinate: Coordinate) -> Coordinates:
        """Return canonical domain coordinates from one validated graph coordinate."""
        if not isinstance(coordinate, Coordinate):
            raise TypeError("Graph coordinate mapping requires a Coordinate.")
        return Coordinates(
            latitude=coordinate.latitude,
            longitude=coordinate.longitude,
        )
