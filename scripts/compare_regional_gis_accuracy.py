"""Read-only comparison of GIS analysis results: Pakistan-wide vs regional Swat data.

Temporary validation script for Hotfix 14.4 (not part of production or the test
suite, and safe to delete once the comparison is confirmed). It runs the same
real GIS analysis pipeline (``RiverNetworkLoader`` -> ``OSMLoader`` ->
``GISDomainService`` -> ``GISAnalysisTool``) for Mingora's coordinates twice:
once against the original Pakistan-wide sources, once against the new regional
extracts produced by ``scripts/extract_regional_gis_data.py``. It prints both
result sets side by side so the regional files can be trusted before being
wired into ``backend/app/config/graph_dependencies.py``.

This script only reads existing data files; it does not create, modify, or
delete anything.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shapely.geometry.base import BaseGeometry

from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.gis.analysis_tool import GISAnalysisTool
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.models import PreparedFloodContext, SpatialPolicy
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.gis.evidence import FloodEvidence, FloodEvidenceBuilder
from backend.app.gis.geometry import BoundingBox, DistanceResult, Point
from backend.app.gis.processing._spatial import local_metric_crs, transform_geometry
from backend.app.gis.processing.flood_zone import FloodZoneGenerator
from backend.app.gis.processing.infrastructure_impact import InfrastructureImpactCalculator
from backend.app.gis.processing.models import InfrastructureImpactSummary
from backend.app.gis.processing.osm import OSMLoader
from backend.app.gis.processing.population_exposure import PopulationExposureCalculator
from backend.app.gis.processing.worldpop import WorldPopLoader
from backend.app.gis.river.loader import RiverNetworkLoader
from backend.app.models.enums import FloodSeverity
from backend.app.models.flood import Coordinates

_FIXTURE_TIMESTAMP = datetime(2026, 7, 26, tzinfo=UTC)
_MINGORA_COORDINATES = Coordinates(latitude=34.7700, longitude=72.3600)
_SEVERITY = FloodSeverity.MAJOR

_ORIGINAL_OSM_PBF = PROJECT_ROOT / "data/gis/osm/raw/pakistan-latest.osm.pbf"
_ORIGINAL_WORLDPOP_TIF = PROJECT_ROOT / "data/gis/worldpop/raw/pak_ppp_2025.tif"
_REGIONAL_OSM_PBF = PROJECT_ROOT / "data/gis/osm/raw/swat-region.osm.pbf"
_REGIONAL_WORLDPOP_TIF = PROJECT_ROOT / "data/gis/worldpop/raw/swat-region_ppp_2025.tif"

_SEPARATOR = "=" * 70


@dataclass(frozen=True, slots=True)
class _AnalysisResult:
    """Collect the values this comparison reports for one loader stack."""

    label: str
    river_geometry_type: str
    river_length_meters: float
    river_vertex_count: int
    river_bounds: tuple[float, float, float, float]
    flood_area_square_meters: float
    exposed_population: float
    population_density_per_square_kilometer: float
    intersecting_cell_count: int
    infrastructure: InfrastructureImpactSummary


def _static_forecast() -> ForecastResult:
    """Return one deterministic forecast, matching the existing test fixture pattern.

    Flood-zone generation depends only on severity and river geometry (see
    ``FloodZoneGenerator.generate``), not forecast content, so a static forecast
    does not affect the comparison and keeps this script free of live GloFAS I/O.
    """

    point = Point(
        latitude=_MINGORA_COORDINATES.latitude,
        longitude=_MINGORA_COORDINATES.longitude,
    )
    return ForecastResult(
        location=ForecastLocation(
            requested_point=point,
            grid_point=point,
            grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
        ),
        metadata=ForecastMetadata(
            snapshot_path=PROJECT_ROOT
            / "data/glofas/glofas_control_20260726T000000Z.nc",
            dataset_name="cems-glofas-forecast",
            product_type="control_forecast",
            hydrological_model="lisflood",
            system_version="operational",
            forecast_reference_time=_FIXTURE_TIMESTAMP,
            retrieved_at=_FIXTURE_TIMESTAMP,
        ),
        series=ForecastSeries(
            points=(
                ForecastPoint(
                    valid_time=_FIXTURE_TIMESTAMP,
                    lead_time_hours=0,
                    discharge_m3_per_second=600.0,
                ),
            )
        ),
    )


def _count_vertices(geometry: BaseGeometry) -> int:
    """Recursively count coordinate vertices across a possibly-multi geometry."""

    if hasattr(geometry, "geoms"):
        return sum(_count_vertices(part) for part in geometry.geoms)
    return len(geometry.coords)


def _run_analysis(
    label: str,
    osm_pbf_path: Path,
    worldpop_tif_path: Path,
    bounds: BoundingBox,
    forecast: ForecastResult,
) -> _AnalysisResult:
    """Run the real production GIS pipeline against one loader stack."""

    river_loader = RiverNetworkLoader(osm_pbf_path)
    osm_loader = OSMLoader(osm_pbf_path)
    worldpop_loader = WorldPopLoader(worldpop_tif_path)
    try:
        river = river_loader.get_geometry(bounds)
        metric_crs = local_metric_crs(river.geometry, river.crs)
        metric_geometry = transform_geometry(river.geometry, river.crs, metric_crs)

        gis_domain_service = GISDomainService(
            river_loader=river_loader,
            osm_loader=osm_loader,
            gis_analysis_tool=GISAnalysisTool(
                FloodZoneGenerator(),
                PopulationExposureCalculator(worldpop_loader),
                InfrastructureImpactCalculator(),
                FloodEvidenceBuilder(),
            ),
        )
        request = GISRequestFactory().build(
            PreparedFloodContext(
                forecast=forecast,
                severity=_SEVERITY,
                bounds=bounds,
                coordinates=_MINGORA_COORDINATES,
            )
        )
        evidence: FloodEvidence = asyncio.run(gis_domain_service.execute(request))
    finally:
        river_loader.close()
        osm_loader.close()
        worldpop_loader.close()

    return _AnalysisResult(
        label=label,
        river_geometry_type=river.geometry.geom_type,
        river_length_meters=float(metric_geometry.length),
        river_vertex_count=_count_vertices(river.geometry),
        river_bounds=river.geometry.bounds,
        flood_area_square_meters=evidence.flood_area_square_meters,
        exposed_population=evidence.population_exposure.exposed_population,
        population_density_per_square_kilometer=(
            evidence.population_exposure.population_density_per_square_kilometer
        ),
        intersecting_cell_count=evidence.population_exposure.intersecting_cell_count,
        infrastructure=evidence.infrastructure_impact,
    )


def _relative_difference(original: float, regional: float) -> float:
    """Return the relative difference between two values, safe for a zero baseline."""

    if original == 0:
        return 0.0 if regional == 0 else float("inf")
    return abs(regional - original) / abs(original)


def _print_row(name: str, original: object, regional: object, match: bool) -> None:
    """Print one aligned comparison row."""

    status = "MATCH" if match else "DIFFER"
    print(f"{name:<32} {str(original):<20} {str(regional):<20} {status}")


def _print_comparison(original: _AnalysisResult, regional: _AnalysisResult) -> None:
    """Print every compared metric side by side with a pass/fail verdict."""

    print(f"{'Metric':<32} {'Original':<20} {'Regional':<20} {'Result'}")
    print("-" * 70)

    length_diff = _relative_difference(
        original.river_length_meters, regional.river_length_meters
    )
    _print_row(
        "River geometry type",
        original.river_geometry_type,
        regional.river_geometry_type,
        original.river_geometry_type == regional.river_geometry_type,
    )
    _print_row(
        "River length (m)",
        f"{original.river_length_meters:.2f}",
        f"{regional.river_length_meters:.2f}",
        length_diff < 1e-6,
    )
    _print_row(
        "River vertex count",
        original.river_vertex_count,
        regional.river_vertex_count,
        original.river_vertex_count == regional.river_vertex_count,
    )
    _print_row(
        "River bounds",
        tuple(round(v, 6) for v in original.river_bounds),
        tuple(round(v, 6) for v in regional.river_bounds),
        original.river_bounds == regional.river_bounds,
    )

    area_diff = _relative_difference(
        original.flood_area_square_meters, regional.flood_area_square_meters
    )
    _print_row(
        "Affected area (sq m)",
        f"{original.flood_area_square_meters:.4f}",
        f"{regional.flood_area_square_meters:.4f}",
        area_diff < 1e-6,
    )

    population_diff = _relative_difference(
        original.exposed_population, regional.exposed_population
    )
    _print_row(
        "Population exposed",
        f"{original.exposed_population:.4f}",
        f"{regional.exposed_population:.4f}",
        population_diff < 1e-6,
    )
    _print_row(
        "Population density (per sq km)",
        f"{original.population_density_per_square_kilometer:.6f}",
        f"{regional.population_density_per_square_kilometer:.6f}",
        _relative_difference(
            original.population_density_per_square_kilometer,
            regional.population_density_per_square_kilometer,
        )
        < 1e-6,
    )
    _print_row(
        "WorldPop intersecting cells",
        original.intersecting_cell_count,
        regional.intersecting_cell_count,
        original.intersecting_cell_count == regional.intersecting_cell_count,
    )

    for field_name in (
        "roads_affected",
        "bridges_affected",
        "schools_affected",
        "hospitals_affected",
        "clinics_affected",
        "police_stations_affected",
        "fire_stations_affected",
        "critical_assets_affected",
    ):
        original_value = getattr(original.infrastructure, field_name)
        regional_value = getattr(regional.infrastructure, field_name)
        _print_row(
            f"Infrastructure: {field_name}",
            original_value,
            regional_value,
            original_value == regional_value,
        )


def main() -> int:
    """Run and print the Pakistan-wide vs regional GIS comparison for Mingora.

    Returns:
        A process exit code indicating whether the comparison ran successfully.
        A non-zero code means a source file was missing or the pipeline failed;
        it does NOT mean the compared results differed (see the printed table).
    """

    for source_path in (
        _ORIGINAL_OSM_PBF,
        _ORIGINAL_WORLDPOP_TIF,
        _REGIONAL_OSM_PBF,
        _REGIONAL_WORLDPOP_TIF,
    ):
        if not source_path.is_file():
            print(f"Regional GIS comparison failed: missing source {source_path}")
            return 1

    spatial_policy_service = SpatialPolicyService(SpatialPolicy())
    bounds = spatial_policy_service.analysis_bounds(_MINGORA_COORDINATES)
    forecast = _static_forecast()

    print(_SEPARATOR)
    print("Flood-Aware Regional GIS Accuracy Comparison (Mingora)")
    print(_SEPARATOR)
    print()
    print(
        "Coordinates: "
        f"latitude={_MINGORA_COORDINATES.latitude}, "
        f"longitude={_MINGORA_COORDINATES.longitude}"
    )
    print(f"Severity: {_SEVERITY.value}")
    print(
        "Analysis bounds: "
        f"min_lat={bounds.min_latitude}, min_lon={bounds.min_longitude}, "
        f"max_lat={bounds.max_latitude}, max_lon={bounds.max_longitude}"
    )
    print()

    started_at = perf_counter()
    original = _run_analysis(
        "Original (Pakistan-wide)",
        _ORIGINAL_OSM_PBF,
        _ORIGINAL_WORLDPOP_TIF,
        bounds,
        forecast,
    )
    regional = _run_analysis(
        "Regional (Swat extract)",
        _REGIONAL_OSM_PBF,
        _REGIONAL_WORLDPOP_TIF,
        bounds,
        forecast,
    )
    elapsed_seconds = perf_counter() - started_at

    _print_comparison(original, regional)
    print()
    print(f"Elapsed time: {elapsed_seconds:.2f} seconds")
    print()
    print("Comparison Complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
