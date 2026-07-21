"""Centralized application configuration."""

from enum import Enum
from functools import lru_cache
from ipaddress import IPv4Address
from pathlib import Path

from pydantic import Field, IPvAnyAddress
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported application deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Supported application logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def _find_project_root(source_file: Path) -> Path:
    """Locate the repository root by finding the nearest project manifest."""

    for directory in source_file.resolve().parents:
        if (directory / "pyproject.toml").is_file():
            return directory

    raise RuntimeError("Unable to locate the project root from the settings module.")


PROJECT_ROOT = _find_project_root(Path(__file__))


class Settings(BaseSettings):
    """Provide validated configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="FLOOD_AWARE_",
        extra="ignore",
    )

    application_name: str = Field(default="Flood-Aware", min_length=1)
    version: str = Field(default="0.1.0", min_length=1)
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_prefix: str = ""
    host: IPvAnyAddress = Field(default=IPv4Address("127.0.0.1"))
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: LogLevel = LogLevel.INFO


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached, validated application settings instance."""

    return Settings()
