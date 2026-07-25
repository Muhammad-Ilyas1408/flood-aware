"""Framework-independent public Weather Tool capability."""

from backend.app.weather.mapper import WeatherMapper
from backend.app.weather.models import WeatherRequest, WeatherResult
from backend.app.weather.protocols import WeatherClientProtocol


class WeatherTool:
    """Retrieve immutable current weather through injected infrastructure dependencies."""

    def __init__(
        self, client: WeatherClientProtocol, mapper: WeatherMapper | None = None
    ) -> None:
        """Initialize the tool with its provider client and payload mapper."""

        self._client = client
        self._mapper = mapper or WeatherMapper()

    def get_current_weather(self, request: WeatherRequest) -> WeatherResult:
        """Validate request type, fetch provider data, and return mapped weather."""

        if not isinstance(request, WeatherRequest):
            raise ValueError("Weather Tool requires a WeatherRequest.")
        return self._mapper.map_current_weather(
            self._client.fetch_current_weather(request)
        )
