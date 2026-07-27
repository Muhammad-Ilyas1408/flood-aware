"""Focused unit tests for the GIS LangGraph orchestration adapter."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.app.forecast.models import (
    ForecastLocation,
    ForecastMetadata,
    ForecastPoint,
    ForecastResult,
    ForecastSeries,
)
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.mappers import FloodEvidenceMapper, GraphCoordinateMapper
from backend.app.graph.nodes import GISAnalysisNode
from backend.app.graph.state import Coordinate
from backend.app.gis.domain.models import GISDomainRequest
from backend.app.gis.geometry import BoundingBox, DistanceResult, Point
from backend.app.models.enums import FloodSeverity


def _forecast_result() -> ForecastResult:
    """Create a validated canonical forecast for node-orchestration tests."""
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


def _state(*, coordinates: Coordinate | None = None):
    """Create immutable graph state with an optional canonical location."""
    return (
        GraphStateFactory()
        .create(coordinates=coordinates)
        .model_copy(update={"forecast_result": _forecast_result()})
    )


def _evidence() -> SimpleNamespace:
    """Create factual GIS output owned by the mocked domain service."""
    return SimpleNamespace(
        flood_zone=SimpleNamespace(severity=FloodSeverity.MAJOR),
        population_exposure=SimpleNamespace(exposed_population=1234.5),
        infrastructure_impact=SimpleNamespace(critical_assets_affected=7),
        flood_area_square_meters=4567.8,
        confidence=0.9,
    )


def _node(*, calls: list[str] | None = None):
    """Create a node with independently inspectable injected dependencies."""
    calls = calls if calls is not None else []
    classifier = Mock()
    spatial_policy = Mock()
    request_factory = Mock()
    domain_service = AsyncMock()
    bounds = BoundingBox(
        min_latitude=33.9,
        min_longitude=71.4,
        max_latitude=34.1,
        max_longitude=71.6,
    )
    request = Mock(spec=GISDomainRequest)
    classifier.classify.side_effect = lambda forecast: calls.append("classify") or (
        FloodSeverity.MAJOR
    )
    spatial_policy.analysis_bounds.side_effect = (
        lambda coordinates: calls.append("bounds") or bounds
    )
    request_factory.build.side_effect = (
        lambda context: calls.append("request") or request
    )

    async def execute(gis_request: GISDomainRequest) -> SimpleNamespace:
        calls.append("execute")
        return _evidence()

    domain_service.execute.side_effect = execute
    return (
        GISAnalysisNode(
            classifier,
            spatial_policy,
            request_factory,
            domain_service,
        ),
        classifier,
        spatial_policy,
        request_factory,
        domain_service,
        request,
    )


def test_node_composes_approved_services_once_in_order() -> None:
    """The adapter should delegate each approved responsibility exactly once."""
    calls: list[str] = []
    node, classifier, spatial_policy, request_factory, domain_service, request = _node(
        calls=calls
    )
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    updated = asyncio.run(node.execute(state))

    classifier.classify.assert_called_once_with(state.forecast_result)
    spatial_policy.analysis_bounds.assert_called_once()
    request_factory.build.assert_called_once()
    domain_service.execute.assert_awaited_once_with(request)
    assert calls == ["classify", "bounds", "request", "execute"]
    assert updated.gis.flood_zone == FloodSeverity.MAJOR.value
    assert updated.gis.population_exposed == 1234.5
    assert updated.gis.infrastructure_exposed == 7
    assert updated.gis.affected_area == 4567.8
    assert updated.gis.confidence == 0.9


def test_node_prepares_canonical_context_from_state_facts() -> None:
    """The factory should receive one context containing the retained forecast."""
    node, _, _, request_factory, _, _ = _node()
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    asyncio.run(node.execute(state))

    context = request_factory.build.call_args.args[0]
    assert context.forecast is state.forecast_result
    assert context.severity is FloodSeverity.MAJOR
    assert context.coordinates.latitude == 34.0151
    assert context.coordinates.longitude == 71.5249


def test_node_invokes_each_graph_mapper_once() -> None:
    """Graph-boundary conversions should remain outside node orchestration."""
    node, *_ = _node()
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    with (
        patch.object(
            GraphCoordinateMapper,
            "to_domain",
            wraps=GraphCoordinateMapper.to_domain,
        ) as coordinate_mapper,
        patch.object(
            FloodEvidenceMapper,
            "to_graph",
            wraps=FloodEvidenceMapper.to_graph,
        ) as evidence_mapper,
    ):
        asyncio.run(node.execute(state))

    coordinate_mapper.assert_called_once_with(state.user_request.coordinates)
    evidence_mapper.assert_called_once()


def test_node_returns_new_state_without_mutating_unowned_sections() -> None:
    """Only the GIS evidence section should be replaced on successful execution."""
    node, *_ = _node()
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    updated = asyncio.run(node.execute(state))

    assert updated is not state
    assert state.gis.population_exposed is None
    assert updated.forecast_result is state.forecast_result
    assert updated.forecast is state.forecast
    assert updated.weather is state.weather
    assert updated.user_request is state.user_request


def test_node_skips_missing_forecast_without_invoking_dependencies() -> None:
    """GIS skips expected requests that lack the canonical forecast result."""
    node, classifier, spatial_policy, request_factory, domain_service, _ = _node()
    state = GraphStateFactory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(node.execute(state))

    assert updated is state
    classifier.classify.assert_not_called()
    spatial_policy.analysis_bounds.assert_not_called()
    request_factory.build.assert_not_called()
    domain_service.execute.assert_not_called()


def test_node_skips_missing_coordinates_without_invoking_dependencies() -> None:
    """GIS skips expected requests that lack a request location."""
    node, classifier, spatial_policy, request_factory, domain_service, _ = _node()
    state = _state()

    updated = asyncio.run(node.execute(state))

    assert updated is state
    classifier.classify.assert_not_called()
    spatial_policy.analysis_bounds.assert_not_called()
    request_factory.build.assert_not_called()
    domain_service.execute.assert_not_called()


@pytest.mark.parametrize(
    "dependency_name", ("classifier", "spatial", "factory", "service")
)
def test_dependency_failures_become_recoverable_graph_errors(
    dependency_name: str,
) -> None:
    """GIS dependency failures should become recoverable graph-state errors."""
    node, classifier, spatial_policy, request_factory, domain_service, _ = _node()
    failures = {
        "classifier": classifier.classify,
        "spatial": spatial_policy.analysis_bounds,
        "factory": request_factory.build,
        "service": domain_service.execute,
    }
    failures[dependency_name].side_effect = RuntimeError(dependency_name)

    updated = asyncio.run(
        node.execute(
            _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))
        )
    )

    assert updated.gis == updated.gis.__class__()
    assert updated.errors[-1].error_type == "RuntimeError"
    assert updated.errors[-1].message == dependency_name
    assert updated.errors[-1].recoverable is True
    assert updated.errors[-1].source_node == "gis"


def test_node_requires_all_constructor_dependencies() -> None:
    """Production orchestration requires explicit dependency injection."""
    with pytest.raises(TypeError):
        GISAnalysisNode()
