"""Pure mapping from parsed GloFAS arrays to immutable forecast domain models."""

from backend.app.forecast.exceptions import ForecastMappingError
from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.forecast.parser import ParsedForecastSnapshot
from backend.app.gis.distance import haversine_distance
from backend.app.gis.exceptions import GISException
from backend.app.gis.geometry import DistanceResult, Point


class ForecastMapper:
    """Map parsed GloFAS data without downloading, parsing, or interpreting flood risk."""

    def map(self, snapshot: ParsedForecastSnapshot, requested_point: Point) -> ForecastResult:
        """Select the nearest grid cell and build a validated immutable forecast result.

        Args:
            snapshot: Typed raw values extracted by ``NetCDFForecastParser``.
            requested_point: GIS-validated WGS 84 location requested by the caller.

        Returns:
            A domain forecast result for the nearest available GloFAS grid cell.

        Raises:
            ForecastMappingError: If inputs are invalid or parser values are inconsistent.
        """

        if not isinstance(snapshot, ParsedForecastSnapshot):
            raise ForecastMappingError("Forecast mapping requires a parsed GloFAS snapshot.")
        if not isinstance(requested_point, Point):
            raise ForecastMappingError("Forecast mapping requires a GIS Point.")

        try:
            latitude_index, longitude_index, grid_point, grid_distance = _nearest_grid_point(
                requested_point,
                snapshot.latitudes,
                snapshot.longitudes,
            )
            location = ForecastLocation(
                requested_point=requested_point,
                grid_point=grid_point,
                grid_distance=grid_distance,
            )
            metadata = ForecastMetadata(
                snapshot_path=snapshot.snapshot_path,
                dataset_name=snapshot.dataset_name,
                product_type=snapshot.product_type,
                hydrological_model=snapshot.hydrological_model,
                system_version=snapshot.system_version,
                forecast_reference_time=snapshot.forecast_reference_time,
                retrieved_at=snapshot.retrieved_at,
            )
            points = tuple(
                ForecastPoint(
                    valid_time=valid_time,
                    lead_time_hours=lead_time_hours,
                    discharge_m3_per_second=snapshot.discharge_values[index][latitude_index][
                        longitude_index
                    ],
                )
                for index, (valid_time, lead_time_hours) in enumerate(
                    zip(snapshot.valid_times, snapshot.lead_time_hours, strict=True)
                )
            )
            return ForecastResult(
                location=location,
                metadata=metadata,
                series=ForecastSeries(points=points),
            )
        except ForecastMappingError:
            raise
        except (GISException, IndexError, ValueError) as error:
            raise ForecastMappingError("Parsed GloFAS data cannot form a forecast result.") from error


def _nearest_grid_point(
    requested_point: Point,
    latitudes: tuple[float, ...],
    longitudes: tuple[float, ...],
) -> tuple[int, int, Point, DistanceResult]:
    """Return the nearest grid location using the shared GIS Haversine implementation."""

    candidates = tuple(
        (
            latitude_index,
            longitude_index,
            Point(latitude=latitude, longitude=longitude),
        )
        for latitude_index, latitude in enumerate(latitudes)
        for longitude_index, longitude in enumerate(longitudes)
    )
    if not candidates:
        raise ForecastMappingError("GloFAS snapshot has no available grid coordinates.")
    latitude_index, longitude_index, grid_point = min(
        candidates,
        key=lambda candidate: haversine_distance(requested_point, candidate[2]).kilometers,
    )
    return (
        latitude_index,
        longitude_index,
        grid_point,
        haversine_distance(requested_point, grid_point),
    )
