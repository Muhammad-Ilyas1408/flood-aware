"""Flood-Aware Agent page: grounded flood-decision conversation via the API."""

import streamlit as st

from api_client import BackendUnavailableError, fetch_villages
from components.conversation import (
    init_session_state,
    render_history,
    submit_turn,
)
from components.header import render_header

st.set_page_config(
    page_title="Flood-Aware Agent - Flood-Aware", page_icon="🧭", layout="wide"
)
render_header()

_SESSION_KEY = "agent_session_id"
_MESSAGES_KEY = "agent_messages"
_MANUAL_ENTRY_OPTION = "Other / not listed"

init_session_state(_SESSION_KEY, _MESSAGES_KEY)

st.title("Flood-Aware Agent")
st.write(
    "Ask about flood risk, shelter capacity, or recommended actions for a "
    "village. Responses are grounded decisions from the Flood-Aware backend."
)

header_col1, header_col2 = st.columns([3, 1])
with header_col2:
    if st.button("Start new conversation", use_container_width=True):
        st.session_state[_SESSION_KEY] = None
        st.session_state[_MESSAGES_KEY] = []
        st.rerun()

with st.container(border=True):
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
    village_options = sorted(village_lookup) + [_MANUAL_ENTRY_OPTION]
    selected_option = st.selectbox(
        "Village",
        village_options,
        index=None,
        placeholder="Select a village...",
        key="chat_village_option",
    )

    if selected_option == _MANUAL_ENTRY_OPTION:
        village_name = st.text_input("Village name (optional)", key="chat_village_name")
        district = st.text_input("District (optional)", key="chat_district")
        coordinates = None
    elif selected_option is not None:
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
        village_name = None
        district = None
        coordinates = None

    province = st.text_input("Province (optional)", key="chat_province")

history_container = st.container(border=True)

prompt = st.chat_input("Ask about flood risk, shelters, or recommended actions...")
if prompt:
    st.session_state[_MESSAGES_KEY].append({"role": "user", "content": prompt})

with history_container:
    render_history(
        st.session_state[_MESSAGES_KEY],
        empty_message=(
            "Ask about flood risk, shelters, or recommended actions to "
            "start the conversation."
        ),
    )

    if prompt:
        with st.chat_message("assistant"):
            submit_turn(
                prompt,
                session_key=_SESSION_KEY,
                messages_key=_MESSAGES_KEY,
                village_name=village_name or None,
                district=district or None,
                province=province or None,
                coordinates=coordinates,
            )
