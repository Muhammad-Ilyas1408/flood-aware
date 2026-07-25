"""Tests for immutable GIS evidence prepared for downstream AI reasoning."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

GIS_EVIDENCE_DEPENDENCIES_AVAILABLE = False

try:
    from shapely.geometry import Polygon

    from backend.app.forecast.models import (
        ForecastLocation,
        ForecastMetadata,
        ForecastPoint,
        ForecastResult,
        ForecastSeries,
    )
    from backend.app.gis.evidence import FloodEvidence, FloodEvidenceBuilder
    from backend.app.gis.geometry import DistanceResult, Point
    from backend.app.gis.processing.exceptions import FloodEvidenceError
    from backend.app.gis.processing.models import (
        ElevationSample,
        FloodZone,
        InfrastructureImpactSummary,
        PopulationExposureResult,
    )
    from backend.app.models.enums import FloodSeverity
except ModuleNotFoundError:
    pass
else:
    GIS_EVIDENCE_DEPENDENCIES_AVAILABLE = True


@unittest.skipIf(
    not GIS_EVIDENCE_DEPENDENCIES_AVAILABLE,
    "GIS evidence dependencies are not installed in this Python environment.",
)
class FloodEvidenceTests(unittest.TestCase):
    """Verify that existing GIS facts become one deterministic AI-ready record."""

    def test_builder_aggregates_existing_facts_without_recalculation(self) -> None:
        """The evidence retains canonical inputs and reuses established values."""

        forecast = _forecast_result()
        flood_zone = _flood_zone()
        population = _population_exposure()
        impact = _infrastructure_impact()
        elevation = ElevationSample(elevation_meters=875.0)

        evidence = FloodEvidenceBuilder().build(
            forecast,
            flood_zone,
            population,
            impact,
            dem_elevation=elevation,
            confidence=0.9,
        )

        self.assertIs(evidence.forecast, forecast)
        self.assertIs(evidence.flood_zone, flood_zone)
        self.assertIs(evidence.population_exposure, population)
        self.assertIs(evidence.infrastructure_impact, impact)
        self.assertIs(evidence.dem_elevation, elevation)
        self.assertEqual(
            evidence.flood_area_square_meters, population.area_analyzed_square_meters
        )
        self.assertEqual(evidence.timestamp, forecast.metadata.retrieved_at)
        self.assertEqual(evidence.flood_zone.severity, FloodSeverity.MAJOR)
        self.assertEqual(evidence.infrastructure_impact.hospitals_affected, 1)
        self.assertEqual(
            evidence.forecast.metadata.dataset_name, "cems-glofas-forecast"
        )

    def test_evidence_is_immutable_and_deterministic(self) -> None:
        """Repeated assembly preserves equal factual output and forbids mutation."""

        builder = FloodEvidenceBuilder()
        arguments = (
            _forecast_result(),
            _flood_zone(),
            _population_exposure(),
            _infrastructure_impact(),
        )

        first = builder.build(*arguments)
        second = builder.build(*arguments)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.confidence = 0.5

    def test_invalid_evidence_inputs_raise_domain_errors(self) -> None:
        """Invalid evidence cannot enter a downstream AI reasoning workflow."""

        with self.assertRaises(FloodEvidenceError):
            FloodEvidenceBuilder().build(
                _forecast_result(),
                _flood_zone(),
                object(),
                _infrastructure_impact(),
            )
        with self.assertRaises(FloodEvidenceError):
            FloodEvidence(
                forecast=_forecast_result(),
                flood_zone=_flood_zone(),
                flood_area_square_meters=1.0,
                population_exposure=_population_exposure(),
                infrastructure_impact=_infrastructure_impact(),
                timestamp=datetime(2026, 7, 25),
            )


def _forecast_result() -> ForecastResult:
    """Build a minimal immutable forecast fixture with complete provenance."""

    timestamp = datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc)
    point = Point(latitude=34.9, longitude=72.2)
    return ForecastResult(
        location=ForecastLocation(
            requested_point=point,
            grid_point=point,
            grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
        ),
        metadata=ForecastMetadata(
            snapshot_path=Path("data/glofas/glofas_control_20260725T080000Z.nc"),
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
                    discharge_m3_per_second=500.0,
                ),
            )
        ),
    )


def _flood_zone() -> FloodZone:
    """Build a deterministic flood-zone fixture."""

    return FloodZone(
        geometry=Polygon(((72.1, 34.8), (72.3, 34.8), (72.3, 35.0), (72.1, 35.0))),
        crs="EPSG:4326",
        severity=FloodSeverity.MAJOR,
        buffer_meters=600.0,
    )


def _population_exposure() -> PopulationExposureResult:
    """Build fixed population facts without running a raster calculation."""

    return PopulationExposureResult(
        exposed_population=5432.0,
        area_analyzed_square_meters=1_250_000.0,
        population_density_per_square_kilometer=4345.6,
        intersecting_cell_count=12,
        minimum_cell_population=10.0,
        maximum_cell_population=1000.0,
        mean_cell_population=452.6,
    )


def _infrastructure_impact() -> InfrastructureImpactSummary:
    """Build fixed affected-infrastructure counts."""

    return InfrastructureImpactSummary(
        roads_affected=14,
        bridges_affected=2,
        schools_affected=3,
        hospitals_affected=1,
        clinics_affected=2,
        police_stations_affected=1,
        fire_stations_affected=1,
        critical_assets_affected=5,
    )
