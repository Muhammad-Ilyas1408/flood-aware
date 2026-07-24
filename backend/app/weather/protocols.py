"""Structural contracts for Weather Tool dependencies."""

from collections.abc import Mapping
from typing import Protocol

from backend.app.weather.models import WeatherRequest


class WeatherClientProtocol(Protocol):
    """Fetch raw current-weather payloads from a configured provider."""

    def fetch_current_weather(self, request: WeatherRequest) -> Mapping[str, object]:
        """Return the provider response for one validated coordinate request."""

        ...
