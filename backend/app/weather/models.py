"""Immutable structured weather models exposed by the Weather Tool."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WeatherRequest(BaseModel):
    """Validated geographic coordinates for a current-weather request."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class WeatherResult(BaseModel):
    """Immutable current-weather information mapped from OpenWeatherMap."""

    model_config = ConfigDict(frozen=True)

    location: str
    country: str
    latitude: float
    longitude: float
    temperature: float
    feels_like: float
    humidity: int = Field(ge=0, le=100)
    pressure: int = Field(gt=0)
    wind_speed: float = Field(ge=0)
    wind_direction: float | None = Field(default=None, ge=0, le=360)
    visibility: int | None = Field(default=None, ge=0)
    weather_condition: str
    weather_description: str
    rainfall: float | None = Field(default=None, ge=0)
    timestamp: datetime
    source: str
