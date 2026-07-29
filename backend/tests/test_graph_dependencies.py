"""Focused tests for the production weather/forecast composition-root helpers."""

import pytest

from backend.app.config.graph_dependencies import (
    _build_forecast_provider,
    _build_weather_tool,
)
from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.forecast.forecast_tool import GloFASForecastTool
from backend.app.forecast.settings import ForecastSettings
from backend.app.weather.client import OpenWeatherClient
from backend.app.weather.settings import WeatherSettings
from backend.app.weather.weather_tool import WeatherTool


def test_build_weather_tool_fails_fast_without_api_key() -> None:
    """Composing the real weather tool must fail fast without a configured key."""
    with pytest.raises(ApplicationConfigurationError):
        _build_weather_tool(WeatherSettings(OPENWEATHER_API_KEY=None))


def test_build_weather_tool_constructs_the_real_tool_with_a_valid_key() -> None:
    """A configured key must produce a real, usable WeatherTool and HTTP client."""
    tool, client = _build_weather_tool(WeatherSettings(OPENWEATHER_API_KEY="test-key"))

    assert isinstance(tool, WeatherTool)
    assert isinstance(client, OpenWeatherClient)
    client.close()


def test_build_forecast_provider_constructs_the_real_local_snapshot_tool() -> None:
    """Forecast composition must wire the real GloFAS tool without any network I/O."""
    provider = _build_forecast_provider(ForecastSettings())

    assert isinstance(provider, GloFASForecastTool)
