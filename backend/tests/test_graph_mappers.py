"""Unit tests for deterministic graph-to-domain boundary mappers."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from shapely.geometry import Point as ShapelyPoint

from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.graph.mappers import FloodEvidenceMapper, GraphCoordinateMapper
from backend.app.graph.state import Coordinate
from backend.app.gis.evidence import FloodEvidence
from backend.app.gis.geometry import DistanceResult, Point
from backend.app.gis.processing.models import (
    FloodZone,
    InfrastructureImpactSummary,
    PopulationExposureResult,
)
from backend.app.models.enums import FloodSeverity


def _forecast_result() -> ForecastResult:
    """Build canonical forecast provenance for flood-evidence mapping tests."""
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    point = Point(latitude=34.0151, longitude=71.5249)
    return ForecastResult(
        location=ForecastLocation(
            requested_point=point,
            grid_point=point,
            grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
        ),
        metadata=ForecastMetadata(
            snapshot_path=Path("data/glofas/test.nc"),
            dataset_name="cems-glofas-forecast",
            product_type="control_forecast",
            hydrological_model="lisflood",
            system_version="operational",
            forecast_reference_time=timestamp,
            retrieved_at=timestamp,
        ),
        series=ForecastSeries(
            points=(
                ForecastPoint(
                    valid_time=timestamp,
                    lead_time_hours=0,
                    discharge_m3_per_second=600.0,
                ),
            )
        ),
    )


def _flood_evidence() -> FloodEvidence:
    """Build factual GIS output for graph evidence projection tests."""
    return FloodEvidence(
        forecast=_forecast_result(),
        flood_zone=FloodZone(
            geometry=ShapelyPoint(71.5249, 34.0151).buffer(0.01),
            crs="EPSG:4326",
            severity=FloodSeverity.MAJOR,
            buffer_meters=600.0,
        ),
        flood_area_square_meters=4567.8,
        population_exposure=PopulationExposureResult(
            exposed_population=1234.5,
            area_analyzed_square_meters=4567.8,
            population_density_per_square_kilometer=270.3,
            intersecting_cell_count=4,
            minimum_cell_population=10.0,
            maximum_cell_population=500.0,
            mean_cell_population=308.625,
        ),
        infrastructure_impact=InfrastructureImpactSummary(
            roads_affected=4,
            bridges_affected=1,
            schools_affected=1,
            hospitals_affected=1,
            clinics_affected=2,
            police_stations_affected=1,
            fire_stations_affected=0,
            critical_assets_affected=7,
        ),
        timestamp=datetime(2026, 7, 26, tzinfo=UTC),
        confidence=0.9,
    )


def test_flood_evidence_mapper_projects_every_owned_graph_field() -> None:
    """Graph evidence should retain every factual field in its state contract."""
    mapped = FloodEvidenceMapper.to_graph(_flood_evidence())

    assert mapped.flood_zone == FloodSeverity.MAJOR.value
    assert mapped.population_exposed == 1234.5
    assert mapped.infrastructure_exposed == 7
    assert mapped.affected_area == 4567.8
    assert mapped.confidence == 0.9


def test_flood_evidence_mapper_is_deterministic_and_returns_immutable_output() -> None:
    """Equal input evidence should yield equal frozen graph-state evidence."""
    evidence = _flood_evidence()
    mapped = FloodEvidenceMapper.to_graph(evidence)

    assert mapped == FloodEvidenceMapper.to_graph(evidence)
    with pytest.raises(ValidationError):
        mapped.population_exposed = 1.0


def test_coordinate_mapper_converts_valid_graph_coordinates() -> None:
    """A graph coordinate should map directly to canonical domain coordinates."""
    mapped = GraphCoordinateMapper.to_domain(
        Coordinate(latitude=34.0151, longitude=71.5249)
    )

    assert mapped.latitude == 34.0151
    assert mapped.longitude == 71.5249


def test_coordinate_mapper_rejects_non_graph_coordinates() -> None:
    """The boundary mapper should fail fast for an invalid source contract."""
    with pytest.raises(TypeError, match="Coordinate"):
        GraphCoordinateMapper.to_domain(object())
