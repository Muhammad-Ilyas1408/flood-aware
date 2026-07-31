"""Situation Room page: dataset, village, and shelter overview from the API."""

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from api_client import (
    BackendUnavailableError,
    fetch_dataset_catalog,
    fetch_shelters,
    fetch_villages,
)
from components.header import render_header
from config import API_BASE_URL

st.set_page_config(
    page_title="Situation Room - Flood-Aware", page_icon="🗺️", layout="wide"
)
render_header()

st.title("Situation Room")
st.write(
    "Live overview of the configured village and shelter datasets served by the "
    "Flood-Aware backend: dataset provenance, record tables, and known spatial "
    "coverage."
)


def _show_backend_error(exc: BackendUnavailableError) -> None:
    """Render a friendly error message for a failed backend call."""

    st.error(
        "Unable to reach the Flood-Aware backend. Please confirm the API server "
        f"is running at {API_BASE_URL}."
    )
    st.caption(str(exc))


with st.container(border=True):
    st.subheader("Dataset Catalog")
    try:
        with st.spinner("Loading dataset catalog..."):
            catalog = fetch_dataset_catalog()
    except BackendUnavailableError as exc:
        _show_backend_error(exc)
        st.stop()

    village_meta = catalog["villages"]["metadata"]
    village_stats = catalog["villages"]["statistics"]
    shelter_meta = catalog["shelters"]["metadata"]
    shelter_stats = catalog["shelters"]["statistics"]

    catalog_col1, catalog_col2 = st.columns(2)
    with catalog_col1:
        st.metric("Village dataset records", village_stats["record_count"])
        st.caption(
            f"**{village_meta['name']}** (v{village_meta['version']}) — "
            f"source: {village_meta['source']}"
        )
    with catalog_col2:
        st.metric("Shelter dataset records", shelter_stats["record_count"])
        st.caption(
            f"**{shelter_meta['name']}** (v{shelter_meta['version']}) — "
            f"source: {shelter_meta['source']}"
        )

with st.container(border=True):
    st.subheader("Villages")
    try:
        with st.spinner("Loading villages..."):
            villages = fetch_villages()
    except BackendUnavailableError as exc:
        _show_backend_error(exc)
        st.stop()

    villages_df = pd.DataFrame(villages)
    if villages_df.empty:
        st.info("No village records returned by the backend.")
    else:
        village_districts = sorted(villages_df["district"].unique())
        selected_village_districts = st.multiselect(
            "Filter villages by district", village_districts, key="village_district_filter"
        )
        if selected_village_districts:
            village_mask = villages_df["district"].isin(selected_village_districts)
            villages_df = villages_df[village_mask]
        st.dataframe(villages_df, use_container_width=True, hide_index=True)

with st.container(border=True):
    st.subheader("Shelters")
    try:
        with st.spinner("Loading shelters..."):
            shelters = fetch_shelters()
    except BackendUnavailableError as exc:
        _show_backend_error(exc)
        st.stop()

    shelters_df = pd.DataFrame(shelters)
    if shelters_df.empty:
        st.info("No shelter records returned by the backend.")
    else:
        shelter_districts = sorted(shelters_df["district"].unique())
        selected_shelter_districts = st.multiselect(
            "Filter shelters by district", shelter_districts, key="shelter_district_filter"
        )
        if selected_shelter_districts:
            shelter_mask = shelters_df["district"].isin(selected_shelter_districts)
            shelters_df = shelters_df[shelter_mask]
        st.dataframe(shelters_df, use_container_width=True, hide_index=True)

with st.container(border=True):
    st.subheader("Spatial Coverage")
    st.info(
        "The `/villages` and `/shelters` endpoints do not return per-record "
        "coordinates, so individual village and shelter markers cannot be plotted. "
        "The map below shows only the real dataset-level bounding box reported by "
        "`/datasets/catalog`, where configured."
    )

    village_bounds = village_meta.get("spatial_bounds")
    shelter_bounds = shelter_meta.get("spatial_bounds")

    if not village_bounds and not shelter_bounds:
        st.warning("No spatial bounds are configured for either dataset.")
    else:
        all_lats: list[float] = []
        all_lons: list[float] = []
        for bounds in (village_bounds, shelter_bounds):
            if bounds:
                box = bounds["bounding_box"]
                all_lats.extend([box["min_latitude"], box["max_latitude"]])
                all_lons.extend([box["min_longitude"], box["max_longitude"]])

        fmap = folium.Map(
            location=[sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons)],
            zoom_start=9,
        )

        if village_bounds:
            box = village_bounds["bounding_box"]
            folium.Rectangle(
                bounds=[
                    [box["min_latitude"], box["min_longitude"]],
                    [box["max_latitude"], box["max_longitude"]],
                ],
                color="#1f77b4",
                fill=True,
                fill_opacity=0.05,
                tooltip="Village dataset extent",
            ).add_to(fmap)

        if shelter_bounds:
            box = shelter_bounds["bounding_box"]
            folium.Rectangle(
                bounds=[
                    [box["min_latitude"], box["min_longitude"]],
                    [box["max_latitude"], box["max_longitude"]],
                ],
                color="#d62728",
                fill=True,
                fill_opacity=0.05,
                tooltip="Shelter dataset extent",
            ).add_to(fmap)

        st_folium(fmap, height=450, use_container_width=True)
