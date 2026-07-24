"""Mapping from OpenWeatherMap payloads to immutable Flood-Aware weather models."""

from collections.abc import Mapping
from datetime import UTC, datetime

from pydantic import ValidationError

from backend.app.weather.exceptions import WeatherMappingError
from backend.app.weather.models import WeatherResult


class WeatherMapper:
    """Translate validated provider payloads without exposing raw JSON upstream."""

    def map_current_weather(self, payload: Mapping[str, object]) -> WeatherResult:
        """Return an immutable WeatherResult from one OpenWeatherMap response."""

        try:
            coordinates = _mapping(payload["coord"])
            main = _mapping(payload["main"])
            wind = _mapping(payload["wind"])
            system = _mapping(payload["sys"])
            weather_entries = payload["weather"]
            if not isinstance(weather_entries, list) or not weather_entries:
                raise TypeError("weather entries are missing")
            weather = _mapping(weather_entries[0])
            rain = payload.get("rain")
            rainfall = _mapping(rain).get("1h") if rain is not None else None
            return WeatherResult(
                location=str(payload["name"]),
                country=str(system["country"]),
                latitude=float(coordinates["lat"]),
                longitude=float(coordinates["lon"]),
                temperature=float(main["temp"]),
                feels_like=float(main["feels_like"]),
                humidity=int(main["humidity"]),
                pressure=int(main["pressure"]),
                wind_speed=float(wind["speed"]),
                wind_direction=_optional_float(wind.get("deg")),
                visibility=_optional_int(payload.get("visibility")),
                weather_condition=str(weather["main"]),
                weather_description=str(weather["description"]),
                rainfall=_optional_float(rainfall),
                timestamp=datetime.fromtimestamp(int(payload["dt"]), tz=UTC),
                source="OpenWeatherMap",
            )
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise WeatherMappingError("OpenWeatherMap payload is missing required weather data.") from error


def _mapping(value: object) -> Mapping[str, object]:
    """Validate one nested JSON object before accessing its fields."""

    if not isinstance(value, Mapping):
        raise TypeError("expected object")
    return value


def _optional_float(value: object) -> float | None:
    """Map an optional numeric provider field."""

    return float(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    """Map an optional integer provider field."""

    return int(value) if value is not None else None
