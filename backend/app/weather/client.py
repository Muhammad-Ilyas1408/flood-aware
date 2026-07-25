"""OpenWeatherMap HTTP infrastructure with explicit failure translation."""

from collections.abc import Mapping

import httpx

from backend.app.weather.exceptions import (
    WeatherAuthenticationError,
    WeatherClientError,
    WeatherConfigurationError,
    WeatherNotFoundError,
)
from backend.app.weather.models import WeatherRequest
from backend.app.weather.settings import WeatherSettings


class OpenWeatherClient:
    """Fetch current weather from OpenWeatherMap without domain mapping logic."""

    def __init__(
        self,
        settings: WeatherSettings,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client with injected HTTP transport when supplied."""

        if not settings.openweather_api_key:
            raise WeatherConfigurationError("OPENWEATHER_API_KEY is required.")
        self._api_key = settings.openweather_api_key
        self._base_url = settings.base_url
        self._weather_units = settings.weather_units
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.timeout_seconds)

    def close(self) -> None:
        """Close the HTTP client only when this instance created it."""

        if self._owns_client:
            self._client.close()

    def fetch_current_weather(self, request: WeatherRequest) -> Mapping[str, object]:
        """Fetch and validate one raw OpenWeatherMap current-weather payload."""

        try:
            response = self._client.get(
                self._base_url,
                params={
                    "lat": request.latitude,
                    "lon": request.longitude,
                    "appid": self._api_key,
                    "units": self._weather_units,
                },
            )
        except httpx.TimeoutException as error:
            raise WeatherClientError("OpenWeatherMap request timed out.") from error
        except httpx.RequestError as error:
            raise WeatherClientError("OpenWeatherMap request failed.") from error
        self._raise_for_status(response)
        try:
            payload = response.json()
        except ValueError as error:
            raise WeatherClientError("OpenWeatherMap returned invalid JSON.") from error
        if not isinstance(payload, dict):
            raise WeatherClientError("OpenWeatherMap returned an invalid payload.")
        return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise WeatherAuthenticationError("OpenWeatherMap rejected the API key.")
        if response.status_code == httpx.codes.NOT_FOUND:
            raise WeatherNotFoundError(
                "OpenWeatherMap could not find the requested location."
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise WeatherClientError(
                "OpenWeatherMap returned an unsuccessful response."
            ) from error
