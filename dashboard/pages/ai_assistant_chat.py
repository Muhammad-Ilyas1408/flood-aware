"""AI Assistant Chat page: grounded flood-decision conversation via the API."""

import threading

import streamlit as st

from api_client import (
    BackendUnavailableError,
    ConversationSessionNotFoundError,
    RecommendationServiceUnavailableError,
    fetch_conversation_turn,
    fetch_villages,
)
from config import API_BASE_URL

st.set_page_config(
    page_title="AI Assistant Chat - Flood-Aware", page_icon="💬", layout="wide"
)

_PROGRESS_MESSAGES = (
    "Analyzing flood zone data...",
    "Reviewing government guidance...",
    "Checking shelter capacity...",
    "Preparing your recommendation...",
)

_RISK_COLORS = {
    "extreme": "red",
    "high": "orange",
    "moderate": "yellow",
    "low": "green",
    "normal": "green",
}
_CONFIDENCE_COLORS = {"high": "green", "medium": "yellow", "low": "orange"}

st.session_state.setdefault("session_id", None)
st.session_state.setdefault("messages", [])


def _run_with_rotating_status(fn, /, *args, **kwargs):
    """Run fn in a background thread, cycling a status placeholder until it returns.

    A single POST /conversation call is one blocking network request with no
    intermediate progress events from the backend, so this only shows honest
    "something is happening" activity, not fabricated per-step progress.
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
        placeholder.markdown(f"_{_PROGRESS_MESSAGES[index % len(_PROGRESS_MESSAGES)]}_")
        index += 1
        thread.join(timeout=2.5)
    placeholder.empty()

    if "error" in result:
        raise result["error"]
    return result["value"]


def _render_decision(message: dict) -> None:
    """Render one grounded decision: badges, summary, priority actions, citations."""

    badge_col1, badge_col2 = st.columns(2)
    with badge_col1:
        st.badge(
            f"Risk: {message['risk_level'].upper()}",
            color=_RISK_COLORS.get(message["risk_level"], "gray"),
        )
    with badge_col2:
        st.badge(
            f"Confidence: {message['confidence'].upper()}",
            color=_CONFIDENCE_COLORS.get(message["confidence"], "gray"),
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


def _render_message(message: dict) -> None:
    """Render one persisted chat message in its chat bubble."""

    with st.chat_message(message["role"]):
        if message.get("type") == "decision":
            _render_decision(message)
        elif message.get("type") == "error":
            st.warning(message["text"])
        else:
            st.markdown(message["content"])


st.title("AI Assistant Chat")
st.write(
    "Ask about flood risk, shelter capacity, or recommended actions for a "
    "village. Responses are grounded decisions from the Flood-Aware backend."
)

header_col1, header_col2 = st.columns([3, 1])
with header_col2:
    if st.button("Start new conversation", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

st.subheader("Location")
try:
    with st.spinner("Loading village list..."):
        villages = fetch_villages()
except BackendUnavailableError:
    villages = []
    st.warning(
        "Could not load the village list from the backend; enter location "
        "details manually below."
    )

village_lookup = {village["name"]: village for village in villages}
village_options = ["(manual entry)"] + sorted(village_lookup)
selected_option = st.selectbox("Village", village_options, key="chat_village_option")

if selected_option != "(manual entry)":
    selected_village = village_lookup[selected_option]
    village_name = selected_option
    district = selected_village["district"]
    coordinates = {
        "latitude": selected_village["latitude"],
        "longitude": selected_village["longitude"],
    }
    st.caption(
        f"District: {district} · "
        f"Coordinates: {coordinates['latitude']:.4f}, {coordinates['longitude']:.4f}"
    )
else:
    village_name = st.text_input("Village name (optional)", key="chat_village_name")
    district = st.text_input("District (optional)", key="chat_district")
    coordinates = None

province = st.text_input("Province (optional)", key="chat_province")

st.divider()

for message in st.session_state.messages:
    _render_message(message)

if prompt := st.chat_input("Ask about flood risk, shelters, or recommended actions..."):
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    _render_message(user_message)

    with st.chat_message("assistant"):
        try:
            payload = _run_with_rotating_status(
                fetch_conversation_turn,
                request_text=prompt,
                session_id=st.session_state.session_id,
                village_name=village_name or None,
                district=district or None,
                province=province or None,
                coordinates=coordinates,
            )
        except ConversationSessionNotFoundError:
            text = "Your session has expired. Starting a new conversation."
            st.session_state.session_id = None
            st.warning(text)
            st.session_state.messages.append(
                {"role": "assistant", "type": "error", "text": text}
            )
        except RecommendationServiceUnavailableError:
            text = (
                "The recommendation service is temporarily busy. Please try "
                "again in a moment."
            )
            st.warning(text)
            st.session_state.messages.append(
                {"role": "assistant", "type": "error", "text": text}
            )
        except BackendUnavailableError:
            text = (
                "Unable to reach the Flood-Aware backend. Please confirm the "
                f"API server is running at {API_BASE_URL}."
            )
            st.warning(text)
            st.session_state.messages.append(
                {"role": "assistant", "type": "error", "text": text}
            )
        else:
            st.session_state.session_id = payload["session_id"]
            decision_message = {
                "role": "assistant",
                "type": "decision",
                "risk_level": payload["risk_level"],
                "confidence": payload["confidence"],
                "summary": payload["summary"],
                "actions": list(payload["actions"]),
                "citations": list(payload["citations"]),
            }
            _render_decision(decision_message)
            st.session_state.messages.append(decision_message)
