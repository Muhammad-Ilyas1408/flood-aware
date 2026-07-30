"""Dashboard-local configuration for calling the Flood-Aware backend API.

The dashboard is a separate Streamlit process from the FastAPI backend, so it
needs its own base URL. This mirrors the backend's default bind address
(`backend/app/config/settings.py`: host 127.0.0.1, port 8000, no path prefix)
and can be overridden without touching backend configuration.
"""

import os

_DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
_configured_base_url = os.environ.get("FLOOD_AWARE_API_BASE_URL", _DEFAULT_API_BASE_URL)
API_BASE_URL = _configured_base_url.rstrip("/")
API_TIMEOUT_SECONDS = 15.0
# /conversation invokes the LLM-backed decision engine, far slower than the
# plain dataset lookups the other endpoints use. Measured turn times ranged
# from ~30s (best case, after the GIS caching fix) up to several minutes,
# with retry-with-feedback correction cycles adding further time on top.
CONVERSATION_TIMEOUT_SECONDS = 180.0
