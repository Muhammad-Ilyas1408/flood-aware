"""Focused orchestration tests for the production ForecastNode."""

import asyncio

import pytest

from backend.app.forecast.models import ForecastResult
from backend.app.graph.nodes import ForecastNode
from backend.app.graph.state import Coordinate
from backend.tests.graph_test_support import forecast_result, state_factory


class FakeForecastProvider:
    """Return one immutable canonical forecast while recording requests."""

    def __init__(self, result: ForecastResult) -> None:
        self.result = result
        self.calls: list[tuple[float, float]] = []

    def get_forecast(self, latitude: float, longitude: float) -> ForecastResult:
        """Record one request and return the supplied canonical result."""
        self.calls.append((latitude, longitude))
        return self.result


def test_forecast_node_retains_canonical_result_without_reconstruction() -> None:
    """The node should store the exact provider result and preserve evidence."""
    result = forecast_result()
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(ForecastNode(provider).execute(state))

    assert updated is not state
    assert updated.forecast_result is result
    assert updated.forecast is state.forecast
    assert provider.calls == [(34.0151, 71.5249)]


def test_forecast_node_requires_constructor_injection() -> None:
    """Forecast orchestration must not select or create a provider internally."""
    with pytest.raises(TypeError):
        ForecastNode()
