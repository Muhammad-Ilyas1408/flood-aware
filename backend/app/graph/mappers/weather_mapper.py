"""Map weather-tool contracts across the graph boundary."""

from backend.app.graph.state import Coordinate, WeatherEvidence
from backend.app.weather.models import WeatherRequest, WeatherResult


class WeatherRequestMapper:
    """Translate graph coordinates into immutable weather-tool requests."""

    @staticmethod
    def to_domain(coordinate: Coordinate) -> WeatherRequest:
        """Return a validated weather request for one graph coordinate."""
        if not isinstance(coordinate, Coordinate):
            raise TypeError("Weather request mapping requires a Coordinate.")
        return WeatherRequest(
            latitude=coordinate.latitude, longitude=coordinate.longitude
        )


class WeatherEvidenceMapper:
    """Translate canonical weather results into immutable graph evidence."""

    @staticmethod
    def to_graph(result: WeatherResult) -> WeatherEvidence:
        """Return graph evidence without reinterpreting weather facts."""
        return WeatherEvidence(
            temperature=result.temperature,
            rainfall=result.rainfall,
            humidity=result.humidity,
            wind_speed=result.wind_speed,
            weather_condition=result.weather_condition,
            source=result.source,
            observation_time=result.timestamp,
        )
