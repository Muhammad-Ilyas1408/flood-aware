"""Explicit configuration for offline government-knowledge indexing and retrieval."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GovernmentKnowledgeSettings(BaseSettings):
    """Load production knowledge-engine settings from environment or `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="FLOOD_AWARE_RAG_", env_file=".env", extra="ignore"
    )

    pdf_directory: Path = Path("data/knowledge/raw")
    chroma_directory: Path = Path("data/chroma/government")
    collection_name: str = "government_disaster_knowledge"
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    response_model: str = "gpt-4.1-mini"
    semantic_chunk_max_characters: int = Field(default=1800, gt=200)
    maximum_retrieved_chunks: int = Field(default=5, gt=0)
    context_max_characters: int = Field(default=12000, gt=500)
