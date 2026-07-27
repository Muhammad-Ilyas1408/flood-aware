"""Environment-backed configuration for the OpenAI decision provider."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DecisionSettings(BaseSettings):
    """Load decision-provider settings from environment or ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="FLOOD_AWARE_DECISION_", env_file=".env", extra="ignore"
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    model: str = "gpt-4.1-mini"
