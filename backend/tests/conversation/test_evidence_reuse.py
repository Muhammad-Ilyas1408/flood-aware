"""Behavioral tests for deterministic conversation evidence-reuse decisions."""

from backend.app.conversation.evidence_reuse import requires_new_evidence
from backend.app.graph.state import Coordinate, UserRequest


def test_first_turn_requires_fresh_evidence() -> None:
    """A conversation without prior request context must execute the graph."""
    assert requires_new_evidence(None, UserRequest(request_text="Flood outlook?"))


def test_identical_context_reuses_existing_evidence() -> None:
    """Changing only the follow-up wording must retain the active evidence."""
    previous = UserRequest(
        request_text="Flood outlook?", village_name="Mingora", district="Swat"
    )
    current = UserRequest(
        request_text="What about shelters?", village_name="Mingora", district="Swat"
    )

    assert not requires_new_evidence(previous, current)


def test_changed_village_requires_fresh_evidence() -> None:
    """A different named village represents a changed evidence context."""
    previous = UserRequest(request_text="Flood outlook?", village_name="Mingora")
    current = UserRequest(request_text="Flood outlook?", village_name="Saidu Sharif")

    assert requires_new_evidence(previous, current)


def test_changed_coordinates_require_fresh_evidence() -> None:
    """A different spatial location requires new tool-derived evidence."""
    previous = UserRequest(
        request_text="Flood outlook?",
        coordinates=Coordinate(latitude=34.0, longitude=71.0),
    )
    current = UserRequest(
        request_text="Flood outlook?",
        coordinates=Coordinate(latitude=34.1, longitude=71.0),
    )

    assert requires_new_evidence(previous, current)


def test_partial_context_only_refreshes_when_a_supplied_value_changes() -> None:
    """Unspecified follow-up context must not discard prior evidence."""
    previous = UserRequest(
        request_text="Flood outlook?",
        village_name="Mingora",
        province="Khyber Pakhtunkhwa",
    )
    unchanged = UserRequest(
        request_text="What about shelters?",
        province="Khyber Pakhtunkhwa",
    )
    changed = UserRequest(request_text="What about shelters?", district="Swat")

    assert not requires_new_evidence(previous, unchanged)
    assert requires_new_evidence(previous, changed)
