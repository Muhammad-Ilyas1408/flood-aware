"""Thread-safe, instance-owned LRU cache for Rasterio dataset readers."""

from collections import OrderedDict
from pathlib import Path
from threading import RLock

import rasterio
from rasterio.io import DatasetReader

from backend.app.gis.config import GIS_CONFIG
from backend.app.gis.processing.exceptions import GISProcessingError
from backend.app.gis.types import RasterPath


class RasterCache:
    """Lazily cache open raster datasets for a bounded set of configured paths.

    Instances own only datasets they open, are safe for concurrent callers, and must
    be closed by their composition owner when processing is complete.
    """

    def __init__(self, max_entries: int = GIS_CONFIG.raster_cache_max_entries) -> None:
        """Create an empty bounded cache.

        Args:
            max_entries: Maximum concurrently open cached raster datasets.

        Raises:
            ValueError: If the cache capacity is not positive.
        """

        if (
            not isinstance(max_entries, int)
            or isinstance(max_entries, bool)
            or max_entries <= 0
        ):
            raise ValueError("Raster cache max_entries must be a positive integer.")
        self._max_entries = max_entries
        self._datasets: OrderedDict[Path, DatasetReader] = OrderedDict()
        self._lock = RLock()

    def get_dem(self, path: RasterPath) -> DatasetReader:
        """Return the lazily opened cached DEM dataset for ``path``."""

        return self._get(path)

    def get_worldpop(self, path: RasterPath) -> DatasetReader:
        """Return the lazily opened cached WorldPop dataset for ``path``."""

        return self._get(path)

    def clear(self) -> None:
        """Close and remove all cached datasets safely."""

        with self._lock:
            datasets = tuple(self._datasets.values())
            self._datasets.clear()
        for dataset in datasets:
            dataset.close()

    def close(self) -> None:
        """Close all instance-owned datasets; equivalent to ``clear``."""

        self.clear()

    def _get(self, path: RasterPath) -> DatasetReader:
        """Return an LRU-managed open dataset for one validated local path."""

        resolved_path = Path(path)
        if not resolved_path.is_file():
            raise GISProcessingError("Raster cache requires an existing raster file.")
        with self._lock:
            existing = self._datasets.pop(resolved_path, None)
            if existing is not None and not existing.closed:
                self._datasets[resolved_path] = existing
                return existing
            try:
                dataset = rasterio.open(resolved_path)
            except Exception as error:
                raise GISProcessingError(
                    "Raster cache could not open the raster dataset."
                ) from error
            self._datasets[resolved_path] = dataset
            self._evict_excess_locked()
            return dataset

    def _evict_excess_locked(self) -> None:
        """Close least-recently-used datasets while the lock protects cache state."""

        while len(self._datasets) > self._max_entries:
            _, dataset = self._datasets.popitem(last=False)
            dataset.close()
