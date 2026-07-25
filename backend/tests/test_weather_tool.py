"""Unit tests for the isolated OpenWeatherMap Weather Tool."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

WEATHER_DEPENDENCIES_AVAILABLE = False

try:
    import httpx
    from pydantic import ValidationError

    from backend.app.weather.client import OpenWeatherClient
    from backend.app.weather.exceptions import (
        WeatherAuthenticationError,
        WeatherClientError,
        WeatherConfigurationError,
        WeatherMappingError,
        WeatherNotFoundError,
    )
    from backend.app.weather.mapper import WeatherMapper
    from backend.app.weather.models import WeatherRequest
    from backend.app.weather.settings import WeatherSettings
    from backend.app.weather.weather_tool import WeatherTool
except ModuleNotFoundError:
    pass
else:
    WEATHER_DEPENDENCIES_AVAILABLE = True


_PAYLOAD = {
    "coord": {"lon": 72.36, "lat": 34.75},
    "weather": [{"main": "Rain", "description": "moderate rain"}],
    "main": {"temp": 18.5, "feels_like": 18.0, "humidity": 82, "pressure": 1012},
    "visibility": 9000,
    "wind": {"speed": 3.2, "deg": 180},
    "rain": {"1h": 1.4},
    "dt": 1_700_000_000,
    "sys": {"country": "PK"},
    "name": "Mingora",
}


def _settings(weather_units: str = "metric") -> WeatherSettings:
    return WeatherSettings(
        OPENWEATHER_API_KEY="test-key",
        base_url="https://weather.test/current",
        weather_units=weather_units,
    )


def _http_client(status_code: int = 200, payload: object = _PAYLOAD) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


@unittest.skipIf(
    not WEATHER_DEPENDENCIES_AVAILABLE,
    "httpx is not installed in this Python environment.",
)
class WeatherToolTests(unittest.TestCase):
    def test_successful_request_maps_immutable_weather_result(self) -> None:
        tool = WeatherTool(OpenWeatherClient(_settings(), _http_client()))
        result = tool.get_current_weather(
            WeatherRequest(latitude=34.75, longitude=72.36)
        )
        self.assertEqual(result.location, "Mingora")
        self.assertEqual(result.country, "PK")
        self.assertEqual(result.rainfall, 1.4)
        self.assertEqual(result.source, "OpenWeatherMap")
        self.assertIsInstance(result.timestamp, datetime)
        with self.assertRaises(ValidationError):
            result.temperature = 20.0

    def test_client_translates_unauthorized_and_not_found_responses(self) -> None:
        request = WeatherRequest(latitude=34.75, longitude=72.36)
        with self.assertRaises(WeatherAuthenticationError):
            OpenWeatherClient(
                _settings(), _http_client(401, {"message": "Invalid API key"})
            ).fetch_current_weather(request)
        with self.assertRaises(WeatherNotFoundError):
            OpenWeatherClient(
                _settings(), _http_client(404, {"message": "not found"})
            ).fetch_current_weather(request)

    def test_client_translates_timeout_and_missing_configuration(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout", request=request)

        request = WeatherRequest(latitude=34.75, longitude=72.36)
        timeout_client = httpx.Client(transport=httpx.MockTransport(handler))
        with self.assertRaises(WeatherClientError):
            OpenWeatherClient(_settings(), timeout_client).fetch_current_weather(
                request
            )
        with self.assertRaises(WeatherConfigurationError):
            OpenWeatherClient(WeatherSettings(OPENWEATHER_API_KEY=None))

    def test_client_closes_only_internally_owned_http_client(self) -> None:
        owned_client = MagicMock()
        with patch(
            "backend.app.weather.client.httpx.Client", return_value=owned_client
        ):
            client = OpenWeatherClient(_settings())
        client.close()
        owned_client.close.assert_called_once_with()

        injected_client = MagicMock()
        OpenWeatherClient(_settings(), injected_client).close()
        injected_client.close.assert_not_called()

    def test_client_uses_configured_weather_units(self) -> None:
        observed_units: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            observed_units.append(request.url.params["units"])
            return httpx.Response(200, json=_PAYLOAD, request=request)

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        OpenWeatherClient(_settings("imperial"), http_client).fetch_current_weather(
            WeatherRequest(latitude=34.75, longitude=72.36)
        )
        self.assertEqual(observed_units, ["imperial"])

    def test_mapper_and_request_validation_reject_invalid_input(self) -> None:
        with self.assertRaises(WeatherMappingError):
            WeatherMapper().map_current_weather({"name": "Mingora"})
        with self.assertRaises(ValidationError):
            WeatherRequest(latitude=91, longitude=72.36)

    def test_tool_propagates_domain_client_errors(self) -> None:
        class FailingClient:
            def fetch_current_weather(
                self, request: WeatherRequest
            ) -> dict[str, object]:
                raise WeatherClientError("network unavailable")

        with self.assertRaises(WeatherClientError):
            WeatherTool(FailingClient()).get_current_weather(
                WeatherRequest(latitude=34.75, longitude=72.36)
            )
