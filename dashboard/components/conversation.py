"""Shared mechanics for the dashboard's chat-style pages.

The Flood-Aware Agent and Policy Advisor pages both drive a conversation
against POST /conversation: same session-state bookkeeping, same rotating
"something is happening" status, same badge/summary/action/citation
rendering, and the same distinct 404/503/connection-failure handling. What
differs between them - whether there's a location selector, and which
fields get sent as grounding context - stays in each page file.
"""

import threading

import streamlit as st

from api_client import (
    BackendUnavailableError,
    ConversationSessionNotFoundError,
    RecommendationServiceUnavailableError,
    fetch_conversation_turn,
)
from config import API_BASE_URL

PROGRESS_MESSAGES = (
    "Analyzing flood zone data...",
    "Reviewing government guidance...",
    "Checking shelter capacity...",
    "Preparing your recommendation...",
)

RISK_COLORS = {
    "extreme": "red",
    "high": "orange",
    "moderate": "yellow",
    "low": "green",
    "normal": "green",
}
CONFIDENCE_COLORS = {"high": "green", "medium": "yellow", "low": "orange"}


def init_session_state(session_key: str, messages_key: str) -> None:
    """Set up the session-state slots a conversation page needs.

    Each conversational page uses its own pair of keys so that, e.g., the
    Flood-Aware Agent and Policy Advisor conversations never share a
    session_id or message history within the same browser session.
    """

    st.session_state.setdefault(session_key, None)
    st.session_state.setdefault(messages_key, [])


def run_with_rotating_status(
    fn, /, *args, progress_messages: tuple[str, ...] = PROGRESS_MESSAGES, **kwargs
):
    """Run fn in a background thread, cycling a status placeholder until it returns.

    A single POST /conversation call is one blocking network request with no
    intermediate progress events from the backend, so this only shows honest
    "something is happening" activity, not fabricated per-step progress.
    progress_messages lets each page supply wording appropriate to what it
    actually does, instead of every page sharing one hardcoded set.
    """

    result: dict[str, object] = {}

    def _target() -> None:
        try:
            result["value"] = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - re-raised on the main thread below
            result["error"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()

    placeholder = st.empty()
    index = 0
    while thread.is_alive():
        placeholder.markdown(f"_{progress_messages[index % len(progress_messages)]}_")
        index += 1
        thread.join(timeout=2.5)
    placeholder.empty()

    if "error" in result:
        raise result["error"]
    return result["value"]


def render_decision(message: dict, *, show_risk_badges: bool = True) -> None:
    """Render one grounded decision: badges, summary, priority actions, citations.

    show_risk_badges is False on pages like Policy Advisor, where no flood
    risk is being assessed and a risk/confidence badge pair would be
    conceptually wrong. The underlying decision payload is unaffected.
    """

    if show_risk_badges:
        badge_col1, badge_col2 = st.columns(2)
        with badge_col1:
            st.badge(
                f"Risk: {message['risk_level'].upper()}",
                color=RISK_COLORS.get(message["risk_level"], "gray"),
            )
        with badge_col2:
            st.badge(
                f"Confidence: {message['confidence'].upper()}",
                color=CONFIDENCE_COLORS.get(message["confidence"], "gray"),
            )

    st.markdown(message["summary"])

    if message["actions"]:
        st.markdown("**Recommended actions:**")
        for action in message["actions"]:
            priority = action["priority"]
            st.markdown(f"- **[{priority.upper()}]** {action['action']}")

    if message["citations"]:
        with st.expander(f"Citations ({len(message['citations'])})"):
            for citation in message["citations"]:
                st.markdown(f"- {citation}")


def render_message(message: dict, *, show_risk_badges: bool = True) -> None:
    """Render one persisted chat message in its chat bubble."""

    with st.chat_message(message["role"]):
        if message.get("type") == "decision":
            render_decision(message, show_risk_badges=show_risk_badges)
        elif message.get("type") == "error":
            st.warning(message["text"])
        else:
            st.markdown(message["content"])


def render_history(
    messages: list[dict],
    *,
    show_risk_badges: bool = True,
    empty_message: str = "Your conversation will appear here.",
) -> None:
    """Render the full message history, or a hint if there isn't one yet.

    Without this, a fresh conversation leaves its surrounding
    `st.container(border=True)` with nothing inside it - a visibly empty
    box. Rendering a caption instead keeps that container's border
    meaningful even before the first message.
    """

    if not messages:
        st.caption(empty_message)
        return

    for message in messages:
        render_message(message, show_risk_badges=show_risk_badges)


def submit_turn(
    prompt: str,
    *,
    session_key: str,
    messages_key: str,
    village_name: str | None = None,
    district: str | None = None,
    province: str | None = None,
    coordinates: dict[str, float] | None = None,
    show_risk_badges: bool = True,
    progress_messages: tuple[str, ...] = PROGRESS_MESSAGES,
) -> None:
    """Send one chat turn and append the resulting message(s) to session state.

    Must be called from within an `st.chat_message("assistant")` block so a
    successful decision renders in place. progress_messages lets each page
    override the rotating "something is happening" wording to match what
    that page actually does (e.g. policy lookup vs. GIS/weather analysis).
    """

    try:
        payload = run_with_rotating_status(
            fetch_conversation_turn,
            progress_messages=progress_messages,
            request_text=prompt,
            session_id=st.session_state[session_key],
            village_name=village_name,
            district=district,
            province=province,
            coordinates=coordinates,
        )
    except ConversationSessionNotFoundError:
        text = "Your session has expired. Starting a new conversation."
        st.session_state[session_key] = None
        st.warning(text)
        st.session_state[messages_key].append(
            {"role": "assistant", "type": "error", "text": text}
        )
    except RecommendationServiceUnavailableError:
        text = (
            "The recommendation service is temporarily busy. Please try "
            "again in a moment."
        )
        st.warning(text)
        st.session_state[messages_key].append(
            {"role": "assistant", "type": "error", "text": text}
        )
    except BackendUnavailableError:
        text = (
            "Unable to reach the Flood-Aware backend. Please confirm the "
            f"API server is running at {API_BASE_URL}."
        )
        st.warning(text)
        st.session_state[messages_key].append(
            {"role": "assistant", "type": "error", "text": text}
        )
    else:
        st.session_state[session_key] = payload["session_id"]
        decision_message = {
            "role": "assistant",
            "type": "decision",
            "risk_level": payload["risk_level"],
            "confidence": payload["confidence"],
            "summary": payload["summary"],
            "actions": list(payload["actions"]),
            "citations": list(payload["citations"]),
        }
        render_decision(decision_message, show_risk_badges=show_risk_badges)
        st.session_state[messages_key].append(decision_message)
