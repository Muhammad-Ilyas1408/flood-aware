"""Flood-Aware Streamlit dashboard entrypoint."""

import streamlit as st

st.set_page_config(page_title="Flood-Aware Dashboard", page_icon="🌊", layout="wide")

st.title("Flood-Aware Dashboard")
st.write(
    "Use the sidebar to open **Situation Analysis** for a live overview of the "
    "configured village and shelter datasets served by the Flood-Aware backend."
)
