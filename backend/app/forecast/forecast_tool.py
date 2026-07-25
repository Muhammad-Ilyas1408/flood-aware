"""Local-snapshot forecast capability built on parsed GloFAS data."""

from backend.app.forecast.exceptions import ForecastMappingError
from backend.app.forecast.mapper import ForecastMapper
from backend.app.forecast.models import ForecastResult
from backend.app.forecast.parser import NetCDFForecastParser
from backend.app.forecast.snapshot_locator import SnapshotLocator
from backend.app.gis.exceptions import GISException
from backend.app.gis.geometry import Point


class GloFASForecastTool:
    """Load the newest local GloFAS snapshot and return validated forecast data."""

    def __init__(
        self,
        parser: NetCDFForecastParser,
        mapper: ForecastMapper,
        snapshot_locator: SnapshotLocator,
    ) -> None:
        """Initialize the tool with injected parsing and mapping collaborators.

        Args:
            parser: NetCDF parser for locally persisted GloFAS snapshots.
            mapper: Pure mapper that selects the nearest grid and builds domain models.
            snapshot_locator: Locator for raw ``.nc`` snapshots from ingestion.
        """

        self._parser = parser
        self._mapper = mapper
        self._snapshot_locator = snapshot_locator

    def get_forecast(self, latitude: float, longitude: float) -> ForecastResult:
        """Return the newest locally stored forecast for one requested coordinate pair.

        Args:
            latitude: Requested WGS 84 latitude.
            longitude: Requested WGS 84 longitude.

        Returns:
            Immutable GloFAS forecast data for the nearest available grid cell.

        Raises:
            ForecastSnapshotNotFoundError: If no local NetCDF snapshot exists.
            ForecastMappingError: If requested coordinates are invalid.
            ForecastParsingError: If the newest snapshot is invalid or unsupported.
        """

        try:
            requested_point = Point(latitude=latitude, longitude=longitude)
        except GISException as error:
            raise ForecastMappingError("Forecast coordinates are invalid.") from error

        snapshot = self._parser.parse(self._snapshot_locator.newest_snapshot())
        return self._mapper.map(snapshot, requested_point)
