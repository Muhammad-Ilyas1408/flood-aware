"""Focused orchestration tests for the production ForecastNode."""

import asyncio
from datetime import UTC, datetime

import pytest

from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.forecast.models import ForecastPoint, ForecastResult
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


def _classification_service() -> FloodClassificationService:
    """Build a real classifier with clear round-number discharge thresholds.

    Mirrors the identical helper in ``test_village_summary_service.py`` --
    kept local rather than shared, since it's a two-line pure construction
    with no other coupling between the two test modules.
    """
    return FloodClassificationService(
        FloodClassificationPolicy(
            moderate_discharge=100.0,
            major_discharge=200.0,
            extreme_discharge=300.0,
        )
    )


class _RaisingClassificationService:
    """Simulate a classification failure without depending on real thresholds."""

    def classify(self, forecast: ForecastResult) -> None:
        """Always raise, regardless of the supplied forecast."""
        raise RuntimeError("classification failed")


def test_forecast_node_retains_canonical_result_and_records_snapshot_age() -> None:
    """The node should store the exact provider result and its derived snapshot age."""
    result = forecast_result()
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(
            provider,
            _classification_service(),
            clock=lambda: datetime(2026, 7, 26, 2, tzinfo=UTC),
        ).execute(state)
    )

    assert updated is not state
    assert updated.forecast_result is result
    assert updated.forecast.snapshot_age_hours == pytest.approx(2.0)
    assert updated.forecast.snapshot_stale is False
    assert provider.calls == [(34.0151, 71.5249)]


def test_forecast_node_populates_evidence_facts_from_the_peak_discharge_point() -> None:
    """Discharge, severity, source, date, and lead time must all come from one peak point.

    Regression test for the real gap found in live testing: ForecastNode
    previously only ever wrote snapshot-age fields to state.forecast,
    leaving the actual hydrological facts permanently null even though
    forecast_result genuinely had them -- silently starving the decision
    prompt of a citable figure on every request, for every village.
    """
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    peak_time = datetime(2026, 7, 26, 12, tzinfo=UTC)
    result = forecast_result(
        points=(
            ForecastPoint(
                valid_time=timestamp, lead_time_hours=0, discharge_m3_per_second=150.0
            ),
            ForecastPoint(
                valid_time=peak_time, lead_time_hours=12, discharge_m3_per_second=250.0
            ),
        )
    )
    provider = FakeForecastProvider(result)
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(
            provider,
            _classification_service(),
            clock=lambda: datetime(2026, 7, 26, 2, tzinfo=UTC),
        ).execute(state)
    )

    assert updated.forecast.discharge == 250.0, (
        "Must select the peak (maximum-discharge) point across the series, "
        "not the first/nearest-lead-time point, to stay consistent with "
        "the severity classification -- which also uses the maximum."
    )
    assert updated.forecast.severity == "major"
    assert updated.forecast.source == "cems-glofas-forecast"
    assert updated.forecast.forecast_date == peak_time
    assert updated.forecast.lead_time == 12


def test_forecast_node_classification_failure_leaves_forecast_fully_default() -> None:
    """A classification failure must not partially populate forecast evidence.

    Guards the atomicity invariant this fix depends on: state.forecast must
    always end up either fully default (genuine absence) or fully populated
    (genuine success), never an in-between state with only snapshot-age
    fields set -- that in-between state was the exact shape of the original
    bug, since evidence-completeness checks compare against the full
    default and would silently treat a half-populated bundle as "present."
    """
    provider = FakeForecastProvider(forecast_result())
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249)
    )

    updated = asyncio.run(
        ForecastNode(provider, _RaisingClassificationService()).execute(state)
    )

    assert updated.forecast_result is None
    assert updated.forecast.discharge is None
    assert updated.forecast.snapshot_age_hours is None
    assert updated.forecast.snapshot_stale is None
    assert len(updated.errors) == 1
    assert updated.errors[0].source_node == "forecast"


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
            _classification_service(),
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
            _classification_service(),
            max_snapshot_age_hours=48,
            clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        ).execute(state)
    )

    assert updated.forecast.snapshot_stale is False
    assert updated.forecast.snapshot_age_hours == pytest.approx(24.0)


def test_forecast_node_requires_constructor_injection() -> None:
    """Forecast orchestration must not select or create its collaborators internally."""
    with pytest.raises(TypeError):
        ForecastNode()


def test_forecast_node_skips_missing_coordinates_without_provider_execution() -> None:
    """Forecast skips expected coordinate-less requests without calling its provider."""
    provider = FakeForecastProvider(forecast_result())
    state = state_factory().create()

    updated = asyncio.run(
        ForecastNode(provider, _classification_service()).execute(state)
    )

    assert updated is state
    assert provider.calls == []
