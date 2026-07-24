"""Domain-specific exceptions for the Weather Tool."""


class WeatherError(Exception):
    """Base exception for Weather Tool failures."""


class WeatherConfigurationError(WeatherError):
    """Raised when required weather configuration is unavailable."""


class WeatherClientError(WeatherError):
    """Raised when OpenWeatherMap cannot provide a valid response."""


class WeatherAuthenticationError(WeatherClientError):
    """Raised when OpenWeatherMap rejects the configured API key."""


class WeatherNotFoundError(WeatherClientError):
    """Raised when OpenWeatherMap cannot find the requested coordinates."""


class WeatherMappingError(WeatherError):
    """Raised when an OpenWeatherMap payload cannot be mapped safely."""
