"""Configuration for the OpenWeatherMap-backed Weather Tool."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WeatherSettings(BaseSettings):
    """Load Weather Tool configuration from environment values and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="FLOOD_AWARE_WEATHER_",
        env_file=".env",
        extra="ignore",
    )

    openweather_api_key: str | None = Field(
        default=None,
        validation_alias="OPENWEATHER_API_KEY",
    )
    base_url: str = "https://api.openweathermap.org/data/2.5/weather"
    timeout_seconds: float = Field(default=10.0, gt=0)
    weather_units: str = "metric"
