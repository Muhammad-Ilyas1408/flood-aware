"""Provider-independent contracts for the Government Disaster Knowledge Engine."""

from abc import ABC, abstractmethod
from collections.abc import Mapping

from backend.app.rag.models import EvidenceContext, GroundedAnswer, KnowledgeChunk


class EmbeddingService(ABC):
    """Embed document passages and user questions without storage knowledge."""

    @abstractmethod
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...


class VectorStore(ABC):
    """Persist and search embedded government knowledge passages."""

    @abstractmethod
    def index(self, chunks: tuple[KnowledgeChunk, ...], vectors: tuple[tuple[float, ...], ...]) -> None: ...

    @abstractmethod
    def search(
        self,
        vector: tuple[float, ...],
        top_k: int,
        filters: Mapping[str, str] | None = None,
        score_threshold: float | None = None,
    ) -> tuple[KnowledgeChunk, ...]: ...


class ResponseGenerator(ABC):
    """Generate raw grounded text from provider-independent prompt strings."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
