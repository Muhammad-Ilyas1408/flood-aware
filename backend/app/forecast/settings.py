"""Validated configuration for the GloFAS snapshot ingestion pipeline."""

from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.forecast.constants import DEFAULT_DATASET_NAME


class ForecastSettings(BaseSettings):
    """Load immutable GloFAS ingestion settings from environment values and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    glofas_api_key: str | None = Field(
        default=None,
        validation_alias="GLOFAS_API_KEY",
    )
    dataset_name: str = Field(
        default=DEFAULT_DATASET_NAME,
        validation_alias="GLOFAS_DATASET_NAME",
        min_length=1,
    )
    glofas_base_url: str = Field(
        default="https://ewds.climate.copernicus.eu/api",
        validation_alias="GLOFAS_BASE_URL",
        min_length=1,
    )
    glofas_request_timeout: float = Field(
        default=120.0,
        validation_alias="GLOFAS_REQUEST_TIMEOUT",
        gt=0,
    )
    glofas_default_forecast_days: int = Field(
        default=1,
        validation_alias="GLOFAS_DEFAULT_FORECAST_DAYS",
        ge=1,
        le=30,
    )

    @field_validator("glofas_base_url")
    @classmethod
    def validate_glofas_base_url(cls, value: str) -> str:
        """Require a direct HTTP(S) EWDS/CDS API endpoint, not rc-file syntax."""

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("GLOFAS_BASE_URL must be an absolute HTTP(S) API URL.")
        return value.rstrip("/")
