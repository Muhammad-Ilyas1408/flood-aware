"""WorldPop raster loading and masked-window access."""

from pathlib import Path
from time import perf_counter

from backend.app.core.logger import get_logger
from backend.app.gis.cache import RasterCache
from backend.app.gis.processing._spatial import transform_geometry
from backend.app.gis.processing.exceptions import WorldPopError
from backend.app.gis.processing.models import FloodZone, RasterMetadata
from backend.app.gis.raster.utilities import clip_to_geometry, extract_metadata
from backend.app.gis.types import RasterArray

_LOGGER = get_logger(__name__)


class WorldPopLoader:
    """Load WorldPop metadata and crop raster reads to a supplied flood zone."""

    def __init__(self, path: Path, raster_cache: RasterCache | None = None) -> None:
        """Initialize the loader for one configured WorldPop GeoTIFF.

        Args:
            path: Path to the source WorldPop raster.
            raster_cache: Optional instance-owned cache injected by composition.
        """

        self._path = path
        self._raster_cache = raster_cache or RasterCache()
        self._metadata: RasterMetadata | None = None

    def metadata(self) -> RasterMetadata:
        """Return validated WorldPop metadata without exposing Rasterio objects."""

        try:
            started_at = perf_counter()
            _LOGGER.debug("WorldPop metadata loading started: path=%s", self._path)
            if self._metadata is None:
                self._metadata = extract_metadata(
                    self._raster_cache.get_worldpop(self._path),
                    self._path,
                )
                _LOGGER.info(
                    "WorldPop metadata loaded: path=%s crs=%s duration_ms=%.2f",
                    self._path,
                    self._metadata.crs,
                    (perf_counter() - started_at) * 1000,
                )
            return self._metadata
        except Exception as error:
            raise WorldPopError(
                "WorldPop raster could not be opened or validated."
            ) from error

    def close(self) -> None:
        """Close cached raster resources owned by this loader's injected cache.

        Callers sharing a cache should close that cache at their composition boundary.
        """

        self._raster_cache.close()
        self._metadata = None

    def read_masked(self, flood_zone: FloodZone) -> RasterArray | None:
        """Read only population cells intersecting the supplied flood-zone polygon.

        Args:
            flood_zone: Flood zone defining the requested spatial mask.

        Returns:
            Cropped masked population values, or ``None`` when no cells overlap.

        Raises:
            WorldPopError: If the raster or flood-zone data is invalid.
        """

        if not isinstance(flood_zone, FloodZone):
            raise WorldPopError("WorldPop masking requires a FloodZone.")
        try:
            started_at = perf_counter()
            _LOGGER.debug("WorldPop raster masking started: path=%s", self._path)
            dataset = self._raster_cache.get_worldpop(self._path)
            metadata = self.metadata()
            raster_geometry = transform_geometry(
                flood_zone.geometry,
                flood_zone.crs,
                metadata.crs,
            )
            try:
                values, _ = clip_to_geometry(dataset, raster_geometry)
            except ValueError as error:
                if "do not overlap" in str(error).lower():
                    return None
                raise
        except WorldPopError:
            raise
        except Exception as error:
            raise WorldPopError("WorldPop raster masking failed.") from error
        _LOGGER.info(
            "WorldPop raster masking finished: path=%s crs=%s duration_ms=%.2f",
            self._path,
            metadata.crs,
            (perf_counter() - started_at) * 1000,
        )
        return values
