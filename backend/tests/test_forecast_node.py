"""Focused orchestration tests for the production ForecastNode."""

import asyncio
from datetime import UTC, datetime

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


def test_forecast_node_retains_canonical_result_and_records_snapshot_age() -> None:
    """The node should store the exact provider result and its derived snapshot age."""
    result = forecast_result()
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(
            provider, clock=lambda: datetime(2026, 7, 26, 2, tzinfo=UTC)
        ).execute(state)
    )

    assert updated is not state
    assert updated.forecast_result is result
    assert updated.forecast.snapshot_age_hours == pytest.approx(2.0)
    assert updated.forecast.snapshot_stale is False
    assert provider.calls == [(34.0151, 71.5249)]


def test_forecast_node_flags_stale_snapshot_without_raising() -> None:
    """A snapshot older than the configured threshold is flagged, not an error."""
    result = forecast_result(retrieved_at=datetime(2026, 7, 22, tzinfo=UTC))
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(
            provider,
            max_snapshot_age_hours=48,
            clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        ).execute(state)
    )

    assert updated.errors == ()
    assert updated.forecast_result is result
    assert updated.forecast.snapshot_stale is True
    assert updated.forecast.snapshot_age_hours == pytest.approx(96.0)


def test_forecast_node_respects_configured_staleness_threshold() -> None:
    """A snapshot within the configured threshold must not be flagged stale."""
    result = forecast_result(retrieved_at=datetime(2026, 7, 25, tzinfo=UTC))
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(
            provider,
            max_snapshot_age_hours=48,
            clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        ).execute(state)
    )

    assert updated.forecast.snapshot_stale is False
    assert updated.forecast.snapshot_age_hours == pytest.approx(24.0)


def test_forecast_node_requires_constructor_injection() -> None:
    """Forecast orchestration must not select or create a provider internally."""
    with pytest.raises(TypeError):
        ForecastNode()


def test_forecast_node_skips_missing_coordinates_without_provider_execution() -> None:
    """Forecast skips expected coordinate-less requests without calling its provider."""
    provider = FakeForecastProvider(forecast_result())
    state = state_factory().create()

    updated = asyncio.run(ForecastNode(provider).execute(state))

    assert updated is state
    assert provider.calls == []
