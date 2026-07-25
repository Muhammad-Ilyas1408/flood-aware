"""Population exposure aggregation using masked WorldPop cells."""

from math import isfinite
from time import perf_counter

import numpy as np

from backend.app.core.logger import get_logger
from backend.app.gis.config import GIS_CONFIG
from backend.app.gis.processing._spatial import geometry_area_square_meters
from backend.app.gis.processing.exceptions import PopulationExposureError, WorldPopError
from backend.app.gis.processing.models import FloodZone, PopulationExposureResult
from backend.app.gis.processing.worldpop import WorldPopLoader

_LOGGER = get_logger(__name__)


class PopulationExposureCalculator:
    """Calculate exposure statistics through an injected WorldPop data source."""

    def __init__(self, worldpop_loader: WorldPopLoader) -> None:
        """Initialize the calculator with its raster access dependency."""

        if not isinstance(worldpop_loader, WorldPopLoader):
            raise PopulationExposureError(
                "Population exposure requires a WorldPopLoader."
            )
        self._worldpop_loader = worldpop_loader

    def calculate(self, flood_zone: FloodZone) -> PopulationExposureResult:
        """Aggregate intersecting WorldPop cells for one flood zone.

        Args:
            flood_zone: Valid flood polygon with an explicit CRS.

        Returns:
            Immutable population exposure totals and cell summary statistics.

        Raises:
            PopulationExposureError: If input or masked values are invalid.
        """

        if not isinstance(flood_zone, FloodZone):
            raise PopulationExposureError("Population exposure requires a FloodZone.")
        try:
            started_at = perf_counter()
            _LOGGER.debug(
                "Population exposure calculation started: crs=%s", flood_zone.crs
            )
            area_square_meters = geometry_area_square_meters(
                flood_zone.geometry,
                flood_zone.crs,
            )
            if not isfinite(area_square_meters) or area_square_meters <= 0:
                raise PopulationExposureError(
                    "Flood-zone area must be positive and finite."
                )
            window = self._worldpop_loader.read_masked(flood_zone)
        except (WorldPopError, ValueError) as error:
            raise PopulationExposureError(
                "Population exposure raster access failed."
            ) from error

        values = np.array((), dtype=float) if window is None else window.compressed()
        values = values[np.isfinite(values) & (values >= 0)]
        exposed_population = float(values.sum()) if values.size else 0.0
        density = exposed_population / (
            area_square_meters / GIS_CONFIG.square_meters_per_square_kilometer
        )
        result = PopulationExposureResult(
            exposed_population=exposed_population,
            area_analyzed_square_meters=area_square_meters,
            population_density_per_square_kilometer=density,
            intersecting_cell_count=int(values.size),
            minimum_cell_population=float(values.min()) if values.size else None,
            maximum_cell_population=float(values.max()) if values.size else None,
            mean_cell_population=float(values.mean()) if values.size else None,
        )
        _LOGGER.info(
            "Population exposure calculated: cells=%s population=%s crs=%s duration_ms=%.2f",
            result.intersecting_cell_count,
            result.exposed_population,
            flood_zone.crs,
            (perf_counter() - started_at) * 1000,
        )
        return result
