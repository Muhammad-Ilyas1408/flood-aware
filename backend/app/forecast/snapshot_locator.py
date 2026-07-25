"""Local snapshot discovery for the GloFAS forecast capability."""

from pathlib import Path

from backend.app.forecast.exceptions import ForecastSnapshotNotFoundError


class SnapshotLocator:
    """Locate persisted GloFAS NetCDF snapshots without parsing their contents."""

    def __init__(self, snapshot_directory: Path) -> None:
        """Initialize the locator for one ingestion-owned snapshot directory.

        Args:
            snapshot_directory: Directory containing raw GloFAS ``.nc`` snapshots.
        """

        self._snapshot_directory = snapshot_directory

    def newest_snapshot(self) -> Path:
        """Return the newest GloFAS NetCDF snapshot by mtime and then filename.

        Returns:
            Path to the selected persisted NetCDF snapshot.

        Raises:
            ForecastSnapshotNotFoundError: If the directory is absent or contains no
                matching snapshots.
        """

        if not self._snapshot_directory.is_dir():
            raise ForecastSnapshotNotFoundError(
                "No local GloFAS snapshot directory exists."
            )
        snapshots = tuple(
            path
            for path in self._snapshot_directory.glob("glofas_*.nc")
            if path.is_file()
        )
        if not snapshots:
            raise ForecastSnapshotNotFoundError(
                "No local GloFAS NetCDF snapshot is available."
            )
        return max(snapshots, key=lambda path: (path.stat().st_mtime_ns, path.name))
