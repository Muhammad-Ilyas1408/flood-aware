"""Behavioral tests for canonical immutable graph evidence aggregation."""

import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.app.graph.aggregator import EvidenceAggregator
from backend.app.graph.state import (
    DatasetEvidence,
    ErrorInfo,
    ExecutionTrace,
    ForecastEvidence,
    GISEvidence,
    KnowledgeEvidence,
    NodeStatus,
    ShelterEvidence,
    VillageEvidence,
    WeatherEvidence,
)
from backend.tests.graph_test_support import forecast_result, state_factory


def _complete_state():
    """Create one state containing evidence from every graph producer."""
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    return (
        state_factory()
        .create()
        .model_copy(
            update={
                "weather": WeatherEvidence(
                    temperature=22.5,
                    source="OpenWeatherMap",
                    observation_time=timestamp,
                    confidence=0.8,
                ),
                "forecast_result": forecast_result(),
                "forecast": ForecastEvidence(
                    forecast_date=timestamp,
                    severity="major",
                    source="cems-glofas-forecast",
                    confidence=0.9,
                ),
                "gis": GISEvidence(
                    flood_zone="major",
                    population_exposed=1200.0,
                    confidence=0.7,
                ),
                "villages": (
                    VillageEvidence(
                        village_name="Mingora",
                        population=1000,
                        confidence=0.6,
                    ),
                ),
                "shelters": ShelterEvidence(shelters=("School Hall",), confidence=0.6),
                "knowledge": KnowledgeEvidence(
                    citations=("NDMA Plan:p4", "shared:reference"), confidence=0.9
                ),
                "datasets": DatasetEvidence(
                    datasets=("villages", "shelters"),
                    provenance=("shared:reference",),
                    confidence=1.0,
                ),
            }
        )
    )


def test_aggregator_collects_every_owned_evidence_section_with_provenance() -> None:
    """The bundle should retain each producer's exact immutable evidence object."""
    state = _complete_state()

    updated = asyncio.run(EvidenceAggregator().aggregate(state))

    assert updated is not state
    assert updated.evidence_bundle.weather is state.weather
    assert updated.evidence_bundle.forecast is state.forecast
    assert updated.evidence_bundle.gis is state.gis
    assert updated.evidence_bundle.villages == state.villages
    assert updated.evidence_bundle.shelters is state.shelters
    assert updated.evidence_bundle.knowledge is state.knowledge
    assert updated.evidence_bundle.datasets is state.datasets
    assert [item.evidence_type for item in updated.evidence_bundle.provenance] == [
        "weather",
        "forecast",
        "gis",
        "village",
        "shelter",
        "knowledge",
        "dataset",
    ]
    weather_origin = updated.evidence_bundle.provenance[0]
    assert weather_origin.source == "OpenWeatherMap"
    assert weather_origin.observed_at == state.weather.observation_time
    assert weather_origin.confidence == 0.8


def test_aggregator_detects_duplicate_references_without_losing_origins() -> None:
    """Repeated references should remain associated with both producing tools."""
    updated = asyncio.run(EvidenceAggregator().aggregate(_complete_state()))

    duplicate = updated.evidence_bundle.duplicates[0]
    assert duplicate.reference == "shared:reference"
    assert [origin.evidence_type for origin in duplicate.origins] == [
        "dataset",
        "knowledge",
    ]


def test_aggregator_records_conflicting_severity_without_resolving_it() -> None:
    """Different forecast and GIS severities must both remain visible."""
    state = _complete_state().model_copy(
        update={"gis": GISEvidence(flood_zone="moderate", confidence=0.7)}
    )

    updated = asyncio.run(EvidenceAggregator().aggregate(state))

    conflict = updated.evidence_bundle.conflicts[0]
    assert conflict.subject == "flood_severity"
    assert [(item.evidence_type, item.value) for item in conflict.observations] == [
        ("forecast", "major"),
        ("gis", "moderate"),
    ]


def test_aggregator_preserves_skipped_and_failed_trace_records() -> None:
    """Aggregation must not rewrite runtime-owned failures or skipped decisions."""
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    trace = (
        ExecutionTrace(
            node_name="weather",
            started_at=timestamp,
            finished_at=timestamp,
            duration_ms=0.0,
            status=NodeStatus.COMPLETED,
            retries=0,
            skipped=False,
        ),
        ExecutionTrace(
            node_name="gis",
            started_at=timestamp,
            finished_at=timestamp,
            duration_ms=0.0,
            status=NodeStatus.SKIPPED,
            retries=0,
            skipped=True,
        ),
        ExecutionTrace(
            node_name="knowledge",
            started_at=timestamp,
            finished_at=timestamp,
            duration_ms=0.0,
            status=NodeStatus.FAILED,
            retries=0,
            skipped=False,
            error="retrieval failed",
        ),
    )
    errors = (
        ErrorInfo(
            error_type="KnowledgeError",
            message="retrieval failed",
            recoverable=True,
            source_node="knowledge",
        ),
    )
    state = _complete_state().model_copy(
        update={"execution_trace": trace, "errors": errors}
    )

    updated = asyncio.run(EvidenceAggregator().aggregate(state))

    assert updated.execution_trace is trace
    assert updated.errors is errors


def test_aggregated_bundle_is_immutable_and_does_not_mutate_input_state() -> None:
    """Aggregation must create a frozen bundle while retaining original state."""
    state = _complete_state()
    updated = asyncio.run(EvidenceAggregator().aggregate(state))

    with pytest.raises(ValidationError):
        updated.evidence_bundle.provenance = ()

    assert state.evidence_bundle.provenance == ()
