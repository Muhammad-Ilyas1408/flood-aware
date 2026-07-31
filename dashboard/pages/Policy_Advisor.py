"""Policy Advisor page: grounded guidance for policy and disaster-management questions.

Unlike the Flood-Aware Agent page, this page has no village/coordinate
selector. Every request is sent with village_name and coordinates set to
None, so the backend's existing routing serves it from the Knowledge/Dataset
sources only, skipping GIS/Weather/Forecast - appropriate for policy and
planning questions that aren't tied to a specific location.
"""

import streamlit as st

from components.conversation import (
    init_session_state,
    render_history,
    submit_turn,
)
from components.header import render_header

st.set_page_config(
    page_title="Policy Advisor - Flood-Aware", page_icon="📋", layout="wide"
)
render_header()

_SESSION_KEY = "policy_session_id"
_MESSAGES_KEY = "policy_messages"
_PROGRESS_MESSAGES = (
    "Reviewing government guidance...",
    "Searching official documents...",
    "Cross-referencing disaster-management plans...",
    "Preparing your answer...",
)

init_session_state(_SESSION_KEY, _MESSAGES_KEY)

st.title("Policy Advisor")
st.write(
    "Ask about flood-related government policy, disaster-management plans, "
    "and official guidance. Responses draw on the Flood-Aware backend's "
    "knowledge base and reference datasets rather than any single village's "
    "conditions."
)

header_col1, header_col2 = st.columns([3, 1])
with header_col2:
    if st.button("Start new conversation", use_container_width=True):
        st.session_state[_SESSION_KEY] = None
        st.session_state[_MESSAGES_KEY] = []
        st.rerun()

history_container = st.container(border=True)

prompt = st.chat_input(
    "Ask about flood policy, disaster-management plans, or official guidance..."
)
if prompt:
    st.session_state[_MESSAGES_KEY].append({"role": "user", "content": prompt})

with history_container:
    render_history(
        st.session_state[_MESSAGES_KEY],
        show_risk_badges=False,
        empty_message=(
            "Ask a policy or disaster-management question to start the "
            "conversation."
        ),
    )

    if prompt:
        with st.chat_message("assistant"):
            submit_turn(
                prompt,
                session_key=_SESSION_KEY,
                messages_key=_MESSAGES_KEY,
                village_name=None,
                district=None,
                province=None,
                coordinates=None,
                show_risk_badges=False,
                progress_messages=_PROGRESS_MESSAGES,
            )
