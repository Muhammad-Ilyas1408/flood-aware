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
    # ChromaVectorStore's collection uses Chroma's default HNSW "l2" space
    # (squared Euclidean distance) since no explicit hnsw:space is configured
    # at collection creation — confirmed empirically: get_or_create_collection()
    # with no metadata resolves to hnsw.space == "l2", and Chroma reports the
    # *squared* L2 distance (verified against synthetic vectors: distance 0.01
    # for a 0.1 per-axis offset, distance 2.0 for orthogonal unit vectors).
    # OpenAI's text-embedding-3-small vectors are unit-normalized (documented
    # API behavior), so for unit vectors squared_L2 = 2 * (1 - cosine_similarity).
    # A threshold of 1.3 requires cosine_similarity >= 0.35, a moderate
    # relevance floor meant to reject generic/boilerplate matches while still
    # admitting genuinely relevant passages. Recalibrate against real corpus
    # queries if false positives/negatives are observed in practice.
    retrieval_score_threshold: float = Field(default=1.3, ge=0)
