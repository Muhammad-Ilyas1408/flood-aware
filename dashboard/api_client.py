"""Thin HTTP client for the dashboard to call the Flood-Aware FastAPI backend."""

import httpx

from config import API_BASE_URL, API_TIMEOUT_SECONDS, CONVERSATION_TIMEOUT_SECONDS


class BackendUnavailableError(RuntimeError):
    """Raised when the Flood-Aware backend cannot be reached or returns an error."""


class ConversationSessionNotFoundError(BackendUnavailableError):
    """Raised when the backend no longer recognizes the given conversation session."""


class RecommendationServiceUnavailableError(BackendUnavailableError):
    """Raised when the backend's recommendation service is temporarily unavailable."""


def _get(path: str) -> dict:
    """Issue a GET request against the backend and return the decoded JSON body."""

    try:
        response = httpx.get(f"{API_BASE_URL}{path}", timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise BackendUnavailableError(
            f"The backend returned an error ({exc.response.status_code}) for {path}."
        ) from exc
    except httpx.HTTPError as exc:
        raise BackendUnavailableError(
            f"Unable to reach the Flood-Aware backend at {API_BASE_URL}."
        ) from exc
    return response.json()


def fetch_dataset_catalog() -> dict:
    """Fetch the configured village and shelter dataset catalog summary."""

    return _get("/datasets/catalog")


def fetch_villages() -> list[dict]:
    """Fetch the configured village records."""

    return _get("/villages")["data"]


def fetch_shelters() -> list[dict]:
    """Fetch the configured shelter records."""

    return _get("/shelters")["data"]


def fetch_conversation_turn(
    request_text: str,
    session_id: str | None = None,
    village_name: str | None = None,
    district: str | None = None,
    province: str | None = None,
    coordinates: dict[str, float] | None = None,
) -> dict:
    """Send one conversation turn to the backend and return the grounded decision.

    Raises ConversationSessionNotFoundError (404) or
    RecommendationServiceUnavailableError (503) as distinct outcomes from a
    generic BackendUnavailableError, so callers can react to each differently.
    """

    payload = {
        "request_text": request_text,
        "session_id": session_id,
        "village_name": village_name,
        "district": district,
        "province": province,
        "coordinates": coordinates,
    }
    try:
        response = httpx.post(
            f"{API_BASE_URL}/conversation",
            json=payload,
            timeout=CONVERSATION_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise BackendUnavailableError(
            f"Unable to reach the Flood-Aware backend at {API_BASE_URL}."
        ) from exc

    if response.status_code == httpx.codes.NOT_FOUND:
        raise ConversationSessionNotFoundError(
            "The conversation session was not found."
        )
    if response.status_code == httpx.codes.SERVICE_UNAVAILABLE:
        raise RecommendationServiceUnavailableError(
            "The recommendation service is temporarily unavailable."
        )
    if response.status_code != httpx.codes.OK:
        raise BackendUnavailableError(
            f"The backend returned an error ({response.status_code}) for /conversation."
        )
    return response.json()
