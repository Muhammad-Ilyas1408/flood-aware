"""Focused unit tests for GIS domain-service composition."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from shapely.geometry.base import BaseGeometry

from backend.app.forecast.models import ForecastResult
from backend.app.gis.domain.exceptions import GISDomainServiceError
from backend.app.gis.domain.models import GISDomainRequest, PreparedFloodContext
from backend.app.gis.domain.service import GISDomainService
from backend.app.gis.geometry import BoundingBox
from backend.app.gis.processing.models import InfrastructureLayers
from backend.app.models.enums import FloodSeverity
from backend.app.models.flood import Coordinates


def _request() -> GISDomainRequest:
    """Return one valid immutable public GIS domain request."""
    return GISDomainRequest(
        context=PreparedFloodContext(
            forecast=Mock(spec=ForecastResult),
            severity=FloodSeverity.MAJOR,
            bounds=BoundingBox(
                min_latitude=34.8,
                min_longitude=72.1,
                max_latitude=35.0,
                max_longitude=72.3,
            ),
            coordinates=Coordinates(latitude=34.9, longitude=72.2),
        )
    )


def _service() -> tuple[GISDomainService, Mock, Mock, AsyncMock]:
    """Create injected production-boundary doubles for one test."""
    river_loader = Mock()
    osm_loader = Mock()
    gis_analysis_tool = AsyncMock()
    return (
        GISDomainService(
            river_loader=river_loader,
            osm_loader=osm_loader,
            gis_analysis_tool=gis_analysis_tool,
        ),
        river_loader,
        osm_loader,
        gis_analysis_tool,
    )


def _configure_success(
    river_loader: Mock,
    osm_loader: Mock,
    gis_analysis_tool: AsyncMock,
):
    """Configure one deterministic composed execution result."""
    forecast = Mock(spec=ForecastResult)
    river = Mock()
    river.geometry = Mock(spec=BaseGeometry)
    river.crs = "EPSG:4326"
    infrastructure = Mock(spec=InfrastructureLayers)
    evidence = Mock()
    river_loader.get_geometry.return_value = river
    osm_loader.load.return_value = infrastructure
    gis_analysis_tool.execute.return_value = evidence
    return forecast, river, infrastructure, evidence


def test_service_composes_all_production_boundaries_once() -> None:
    """One execution should acquire each source once and return canonical evidence."""
    service, river_loader, osm_loader, gis_tool = _service()
    _, river, infrastructure, evidence = _configure_success(
        river_loader, osm_loader, gis_tool
    )
    request = _request()

    assert asyncio.run(service.execute(request)) is evidence
    river_loader.get_geometry.assert_called_once_with(request.context.bounds)
    osm_loader.load.assert_called_once_with(request.context.bounds)
    gis_tool.execute.assert_awaited_once()
    analysis_request = gis_tool.execute.await_args.args[0]
    assert analysis_request.forecast is request.context.forecast
    assert analysis_request.river_geometry is river.geometry
    assert analysis_request.infrastructure_layers is infrastructure


@pytest.mark.parametrize("failure_owner", ("river", "osm", "gis"))
def test_component_failures_are_translated(failure_owner: str) -> None:
    """A failing composed boundary should expose one domain-level exception."""
    service, river_loader, osm_loader, gis_tool = _service()
    _configure_success(river_loader, osm_loader, gis_tool)
    dependencies = {
        "river": river_loader.get_geometry,
        "osm": osm_loader.load,
        "gis": gis_tool.execute,
    }
    dependencies[failure_owner].side_effect = RuntimeError("failure")

    with pytest.raises(GISDomainServiceError):
        asyncio.run(service.execute(_request()))


def test_service_execution_order_is_deterministic() -> None:
    """Dependencies should execute in the required production composition order."""
    calls: list[str] = []
    service, river_loader, osm_loader, gis_tool = _service()
    _, _, _, evidence = _configure_success(river_loader, osm_loader, gis_tool)
    river_loader.get_geometry.side_effect = lambda *_: calls.append("river") or Mock(
        geometry=Mock(spec=BaseGeometry), crs="EPSG:4326"
    )
    osm_loader.load.side_effect = lambda *_: calls.append("osm") or Mock(
        spec=InfrastructureLayers
    )
    gis_tool.execute.side_effect = lambda *_: calls.append("gis") or evidence

    assert asyncio.run(service.execute(_request())) is evidence
    assert calls == ["river", "osm", "gis"]


def test_invalid_request_is_rejected_before_dependency_execution() -> None:
    """The public boundary should reject non-domain requests immediately."""
    service, river_loader, _, _ = _service()

    with pytest.raises(GISDomainServiceError):
        asyncio.run(service.execute(object()))

    river_loader.get_geometry.assert_not_called()
