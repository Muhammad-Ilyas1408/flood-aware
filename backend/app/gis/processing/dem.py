"""Copernicus DEM access isolated from Rasterio implementation details."""

from math import isfinite
from pathlib import Path
from time import perf_counter

from pyproj import Transformer

from backend.app.core.logger import get_logger
from backend.app.gis.cache import RasterCache
from backend.app.gis.config import GIS_CONFIG
from backend.app.gis.geometry import Point
from backend.app.gis.processing.exceptions import DEMError
from backend.app.gis.processing.models import ElevationSample, RasterMetadata
from backend.app.gis.raster.utilities import extract_metadata

_LOGGER = get_logger(__name__)


class DEMLoader:
    """Load and query a local DEM while keeping Rasterio private to this component."""

    def __init__(self, path: Path, raster_cache: RasterCache | None = None) -> None:
        """Initialize the loader for one configured local DEM path.

        Args:
            path: Path to the source DEM GeoTIFF.
            raster_cache: Optional instance-owned cache injected by composition.
        """

        self._path = path
        self._raster_cache = raster_cache or RasterCache()
        self._metadata: RasterMetadata | None = None

    def metadata(self) -> RasterMetadata:
        """Return validated local DEM metadata.

        Returns:
            Immutable DEM metadata.

        Raises:
            DEMError: If the configured DEM cannot be opened or validated.
        """

        try:
            started_at = perf_counter()
            _LOGGER.debug("DEM metadata loading started: path=%s", self._path)
            if self._metadata is None:
                self._metadata = extract_metadata(
                    self._raster_cache.get_dem(self._path),
                    self._path,
                )
                _LOGGER.info(
                    "DEM metadata loaded: path=%s crs=%s duration_ms=%.2f",
                    self._path,
                    self._metadata.crs,
                    (perf_counter() - started_at) * 1000,
                )
            return self._metadata
        except Exception as error:
            raise DEMError("DEM could not be opened or validated.") from error

    def close(self) -> None:
        """Close cached raster resources owned by this loader's injected cache.

        Callers sharing a cache should close that cache at their composition boundary.
        """

        self._raster_cache.close()
        self._metadata = None

    def elevation_at(self, point: Point) -> ElevationSample:
        """Return the DEM elevation at a validated WGS84 point.

        Args:
            point: Requested WGS84 location.

        Returns:
            Elevation sample in meters.

        Raises:
            DEMError: If the point is outside the DEM or has no valid elevation.
        """

        if not isinstance(point, Point):
            raise DEMError("DEM elevation lookup requires a GIS Point.")
        try:
            started_at = perf_counter()
            _LOGGER.debug("DEM elevation lookup started: path=%s", self._path)
            dataset = self._raster_cache.get_dem(self._path)
            metadata = self.metadata()
            transformer = Transformer.from_crs(
                GIS_CONFIG.default_crs, metadata.crs, always_xy=True
            )
            x_coordinate, y_coordinate = transformer.transform(
                point.longitude, point.latitude
            )
            left, bottom, right, top = metadata.bounds
            if not left <= x_coordinate <= right or not bottom <= y_coordinate <= top:
                raise DEMError(
                    "Requested location is outside the configured DEM extent."
                )
            value = float(next(dataset.sample([(x_coordinate, y_coordinate)]))[0])
            if not isfinite(value) or (
                metadata.nodata is not None and value == metadata.nodata
            ):
                raise DEMError(
                    "DEM contains no valid elevation at the requested location."
                )
            sample = ElevationSample(elevation_meters=value)
            _LOGGER.info(
                "DEM elevation lookup finished: path=%s crs=%s duration_ms=%.2f",
                self._path,
                metadata.crs,
                (perf_counter() - started_at) * 1000,
            )
            return sample
        except DEMError:
            raise
        except Exception as error:
            raise DEMError("DEM elevation lookup failed.") from error
