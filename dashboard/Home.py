"""Flood-Aware Streamlit dashboard entrypoint."""

import streamlit as st

from components.header import render_header

st.set_page_config(page_title="Flood-Aware Dashboard", page_icon="🌊", layout="wide")
render_header()

st.title("Flood-Aware Dashboard")
st.write(
    "A situational-awareness and decision-support platform for community "
    "flood risk, built on the Flood-Aware backend. Use the sidebar to open "
    "any of the following:"
)

with st.container(border=True):
    st.subheader("🗺️ Situation Room")
    st.write(
        "A live overview of the configured village and shelter datasets: "
        "dataset provenance, record tables, and known spatial coverage."
    )

with st.container(border=True):
    st.subheader("🧭 Flood-Aware Agent")
    st.write(
        "A grounded conversation about flood risk, shelter capacity, and "
        "recommended actions for a specific village."
    )

with st.container(border=True):
    st.subheader("📋 Policy Advisor")
    st.write(
        "A grounded conversation for government policy, disaster-management "
        "plans, and official guidance questions that aren't tied to a "
        "specific village."
    )
