"""Batch embedding infrastructure for government disaster knowledge passages."""

from typing import Protocol

from backend.app.rag.protocols import EmbeddingService


class _Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingService(EmbeddingService):
    """Use LangChain's maintained OpenAI embedding client behind a local contract."""

    def __init__(self, client: _Embedder | None = None, api_key: str | None = None, model: str = "text-embedding-3-small") -> None:
        if client is None:
            if not api_key:
                raise ValueError("An explicit OpenAI API key is required.")
            from langchain_openai import OpenAIEmbeddings
            client = OpenAIEmbeddings(api_key=api_key, model=model)
        self._client = client

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Embed an ordered batch and preserve its exact ordering."""

        if not texts:
            return ()
        return tuple(tuple(vector) for vector in self._client.embed_documents(list(texts)))
