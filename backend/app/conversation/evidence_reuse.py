"""Deterministic evidence-reuse policy for multi-turn conversation."""

from backend.app.graph.state import UserRequest


def requires_new_evidence(previous: UserRequest | None, current: UserRequest) -> bool:
    """Return whether current location context requires a fresh graph run.

    Request text deliberately does not affect this policy: natural-language intent
    is evaluated only by the existing grounded decision agent, never by this
    deterministic reuse boundary.
    """
    if previous is None:
        return True
    return any(
        current_value is not None and current_value != previous_value
        for current_value, previous_value in (
            (current.coordinates, previous.coordinates),
            (current.village_name, previous.village_name),
            (current.district, previous.district),
            (current.province, previous.province),
        )
    )
