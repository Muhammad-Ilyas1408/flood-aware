"""Shared branded header rendered at the top of every dashboard page."""

import streamlit as st

_APP_NAME = "Flood-Aware"
_TAGLINE = "Community flood risk & response platform"
_LOGO = "🌊"


def render_header() -> None:
    """Render the persistent branded title/logo area for the current page.

    `st.set_page_config` still has to be called separately in every page
    file (it controls the browser tab title/icon and must run first), but
    calling this immediately after it keeps the in-page identity - logo,
    name, tagline - identical across all pages. This also renders the
    matching sidebar brand mark, so every page gets both from one call.
    """

    with st.container(border=True):
        logo_col, text_col = st.columns([1, 10], vertical_alignment="center")
        with logo_col:
            st.markdown(f"# {_LOGO}")
        with text_col:
            st.markdown(f"##### {_APP_NAME}")
            st.caption(_TAGLINE)

    _render_sidebar_brand()


def _render_sidebar_brand() -> None:
    """Render a compact brand mark in the sidebar, below Streamlit's page list.

    Streamlit's classic pages/-directory navigation renders its own page
    list at the top of the sidebar before any page script runs, so custom
    content can only be added below it, not above - there's no supported
    way to reorder that in this multipage mode. This also adds a left
    accent bar to whichever nav link is the current page, keyed off the
    real `aria-current="page"` attribute Streamlit's nav sets for
    accessibility (not a private implementation detail), using the theme's
    own primaryColor so it stays in sync with .streamlit/config.toml.
    """

    primary_color = st.get_option("theme.primaryColor") or "#F59E0B"

    with st.sidebar:
        st.markdown(
            f"""
            <style>
            [data-testid="stSidebarNavLink"][aria-current="page"] {{
                border-left: 3px solid {primary_color};
                padding-left: 0.5rem;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption(f"{_LOGO} {_APP_NAME}")
