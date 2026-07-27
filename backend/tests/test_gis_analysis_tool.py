"""Unit tests for production GIS analysis orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point as ShapelyPoint

from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.gis.analysis_tool import GISAnalysisRequest, GISAnalysisTool
from backend.app.gis.evidence import FloodEvidence
from backend.app.gis.exceptions import GISAnalysisError
from backend.app.gis.geometry import DistanceResult, Point
from backend.app.gis.processing.exceptions import FloodZoneError
from backend.app.gis.processing.models import (
    FloodZone,
    InfrastructureImpact,
    InfrastructureImpactSummary,
    InfrastructureLayers,
    PopulationExposureResult,
)
from backend.app.models.enums import FloodSeverity


def _request() -> GISAnalysisRequest:
    """Build immutable input for orchestration tests without external datasets."""
    point = Point(latitude=34.9, longitude=72.2)
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    forecast = ForecastResult(
        location=ForecastLocation(
            requested_point=point,
            grid_point=point,
            grid_distance=DistanceResult(meters=0.0, kilometers=0.0),
        ),
        metadata=ForecastMetadata(
            snapshot_path=Path("snapshot.nc"),
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
    layer = gpd.GeoDataFrame(geometry=[ShapelyPoint(72.2, 34.9)], crs="EPSG:4326")
    return GISAnalysisRequest(
        forecast=forecast,
        severity=FloodSeverity.MAJOR,
        river_geometry=LineString(((72.1, 34.8), (72.3, 35.0))),
        river_crs="EPSG:4326",
        infrastructure_layers=InfrastructureLayers(
            roads=layer,
            bridges=layer,
            schools=layer,
            hospitals=layer,
            clinics=layer,
            police_stations=layer,
            fire_stations=layer,
        ),
    )


def _tool() -> tuple[GISAnalysisTool, Mock, Mock, Mock, Mock]:
    """Create a tool and injected component doubles for one unit test."""
    generator, exposure, impact, builder = (Mock(), Mock(), Mock(), Mock())
    tool = GISAnalysisTool(generator, exposure, impact, builder)
    return tool, generator, exposure, impact, builder


def _configure_success(
    generator: Mock, exposure: Mock, impact: Mock, builder: Mock
) -> FloodEvidence:
    """Configure injected collaborators to return existing canonical outputs."""
    zone = Mock(spec=FloodZone)
    population = Mock(spec=PopulationExposureResult)
    summary = Mock(spec=InfrastructureImpactSummary)
    evidence = Mock(spec=FloodEvidence)
    generator.generate.return_value = zone
    exposure.calculate.return_value = population
    impact.calculate.return_value = Mock(spec=InfrastructureImpact, summary=summary)
    builder.build.return_value = evidence
    return evidence


def test_execute_coordinates_existing_components_once() -> None:
    """The tool should delegate every calculation to exactly one collaborator."""
    tool, generator, exposure, impact, builder = _tool()
    expected = _configure_success(generator, exposure, impact, builder)
    request = _request()

    result = asyncio.run(tool.execute(request))

    assert result is expected
    generator.generate.assert_called_once_with(
        request.severity, request.river_geometry, request.river_crs
    )
    exposure.calculate.assert_called_once_with(generator.generate.return_value)
    impact.calculate.assert_called_once_with(
        generator.generate.return_value, request.infrastructure_layers
    )
    builder.build.assert_called_once()


@pytest.mark.parametrize(
    "failure_owner", ("generator", "exposure", "impact", "builder")
)
def test_component_failures_are_translated(failure_owner: str) -> None:
    """Expected component failures should retain a GIS domain failure boundary."""
    tool, generator, exposure, impact, builder = _tool()
    _configure_success(generator, exposure, impact, builder)
    {
        "generator": generator.generate,
        "exposure": exposure.calculate,
        "impact": impact.calculate,
        "builder": builder.build,
    }[failure_owner].side_effect = FloodZoneError("failure")

    with pytest.raises(GISAnalysisError):
        asyncio.run(tool.execute(_request()))


def test_execute_rejects_invalid_request() -> None:
    """The execution boundary should fail fast before invoking collaborators."""
    tool, generator, _, _, _ = _tool()

    with pytest.raises(GISAnalysisError):
        asyncio.run(tool.execute(object()))

    generator.generate.assert_not_called()


def test_execution_is_deterministic_for_identical_component_outputs() -> None:
    """No additional facts should be introduced by orchestration."""
    tool, generator, exposure, impact, builder = _tool()
    expected = _configure_success(generator, exposure, impact, builder)
    request = _request()

    assert asyncio.run(tool.execute(request)) is expected
    assert asyncio.run(tool.execute(request)) is expected
