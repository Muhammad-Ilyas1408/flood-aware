"""Focused validation tests for immutable graph state and state construction."""

import pytest
from pydantic import ValidationError

from backend.app.ai.models import DecisionContext
from backend.app.graph.mapper import DecisionContextMapper
from backend.app.graph.state import Coordinate, GraphState, RuntimeMode
from backend.tests.graph_test_support import forecast_result, state_factory


def test_graph_state_is_frozen_and_json_serializable() -> None:
    """Graph state should be immutable and support JSON serialization."""
    state = state_factory().create(
        coordinates=Coordinate(latitude=34.0, longitude=71.0)
    )

    with pytest.raises(ValidationError):
        state.user_request = state.user_request

    assert '"runtime_mode":"live"' in state.model_dump_json()


def test_coordinate_rejects_invalid_latitude() -> None:
    """Graph coordinates should fail fast outside WGS84 latitude bounds."""
    with pytest.raises(ValidationError):
        Coordinate(latitude=91, longitude=71)


def test_graph_state_rejects_unknown_fields() -> None:
    """Graph state must not silently accept unowned state fields."""
    state = state_factory().create()
    with pytest.raises(ValidationError):
        GraphState.model_validate({**state.model_dump(), "unknown": "value"})


def test_factory_uses_injected_identifiers_and_clock() -> None:
    """Factory metadata should be deterministic when collaborators are fixed."""
    state = state_factory().create()
    assert str(state.runtime.execution_id).endswith("1")
    assert str(state.runtime.request_id).endswith("2")


def test_context_mapper_preserves_supported_legacy_context_values() -> None:
    """The mapper should construct state without changing DecisionContext."""
    context = DecisionContext(
        context={
            "question": "What is the flood outlook?",
            "latitude": 34.0151,
            "longitude": 71.5249,
            "village_name": "Peshawar",
        }
    )
    state = DecisionContextMapper(state_factory()).map(
        context, runtime_mode=RuntimeMode.SCENARIO
    )

    assert state.user_request.request_text == "What is the flood outlook?"
    assert state.user_request.coordinates == Coordinate(
        latitude=34.0151, longitude=71.5249
    )
    assert state.user_request.village_name == "Peshawar"
    assert state.runtime.runtime_mode is RuntimeMode.SCENARIO


def test_context_mapper_initializes_empty_context_deterministically() -> None:
    """An empty legacy context should produce documented empty state sections."""
    state = DecisionContextMapper(state_factory()).map(DecisionContext())
    assert state.user_request.coordinates is None
    assert state.forecast_result is None
    assert state.forecast_evidence is state.forecast


def test_context_mapper_ignores_incomplete_coordinates() -> None:
    """Missing coordinate pairs must not create partial coordinate state."""
    state = DecisionContextMapper(state_factory()).map(
        DecisionContext(context={"latitude": 34.0})
    )
    assert state.user_request.coordinates is None


def test_forecast_result_state_member_is_immutable_and_serializable() -> None:
    """Canonical forecast state should preserve frozen model guarantees."""
    state = (
        state_factory()
        .create()
        .model_copy(update={"forecast_result": forecast_result()})
    )

    with pytest.raises(ValidationError):
        state.forecast_result.metadata.dataset_name = "different"

    assert '"forecast_result"' in state.model_dump_json()
