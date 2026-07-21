"""Health endpoint response contract."""

from pydantic import ConfigDict, Field

from backend.app.schemas.common import TimestampModel


class HealthResponse(TimestampModel):
    """Describe the running application's health and deployment metadata."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(min_length=1)
    application: str = Field(min_length=1)
    version: str = Field(min_length=1)
    environment: str = Field(min_length=1)
