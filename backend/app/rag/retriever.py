"""Semantic retrieval over authoritative government disaster knowledge."""

from collections.abc import Mapping

from backend.app.rag.models import KnowledgeChunk
from backend.app.rag.protocols import EmbeddingService, VectorStore


class GovernmentRetriever:
    """Retrieve government evidence independently from any response provider."""

    def __init__(self, embeddings: EmbeddingService, vector_store: VectorStore) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        filters: Mapping[str, str] | None = None,
        score_threshold: float | None = None,
    ) -> tuple[KnowledgeChunk, ...]:
        """Embed a question once and return ordered semantic evidence."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError("A non-blank retrieval question is required.")
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        if score_threshold is not None and score_threshold < 0:
            raise ValueError("score_threshold cannot be negative.")
        vector, = self._embeddings.embed((question,))
        return self._vector_store.search(vector, top_k, filters, score_threshold)
