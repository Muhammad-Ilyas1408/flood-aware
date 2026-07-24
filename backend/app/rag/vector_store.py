"""Chroma-backed persistence for government-document embeddings."""

from collections.abc import Mapping
from pathlib import Path

from backend.app.rag.models import ChunkMetadata, KnowledgeChunk
from backend.app.rag.protocols import VectorStore


class ChromaVectorStore(VectorStore):
    """Persist source-rich government chunks and support filtered semantic search."""

    def __init__(self, persist_directory: str | Path, collection_name: str = "government_disaster_knowledge", collection: object | None = None) -> None:
        self._client: object | None = None
        self._collection_name = collection_name
        if collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(persist_directory))
            collection = self._client.get_or_create_collection(collection_name)
        self._collection = collection
        self._chunks: dict[str, KnowledgeChunk] = {}

    def index(self, chunks: tuple[KnowledgeChunk, ...], vectors: tuple[tuple[float, ...], ...]) -> None:
        """Persist chunks and vectors in deterministic input order."""

        if len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors must have equal lengths.")
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks], documents=[c.text for c in chunks],
            embeddings=[list(v) for v in vectors], metadatas=[self._metadata(c) for c in chunks],
        )
        self._chunks.update({c.chunk_id: c for c in chunks})

    def clear(self) -> None:
        """Remove all persisted vectors and the matching in-process identity map."""

        if self._client is not None:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(self._collection_name)
        else:
            identifiers = self._collection.get(include=[]).get("ids", [])
            if identifiers:
                self._collection.delete(ids=identifiers)
        self._chunks.clear()

    def close(self) -> None:
        """Release a persistent Chroma client when its implementation supports it."""

        close = getattr(self._collection, "close", None)
        if callable(close):
            close()

    def search(
        self,
        vector: tuple[float, ...],
        top_k: int,
        filters: Mapping[str, str] | None = None,
        score_threshold: float | None = None,
    ) -> tuple[KnowledgeChunk, ...]:
        """Return Chroma-ranked chunks, rehydrating persisted metadata when needed."""

        result = self._collection.query(
            query_embeddings=[list(vector)],
            n_results=top_k,
            where=dict(filters) if filters else None,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadata = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        matches = zip(ids, documents, metadata, distances, strict=True)
        return tuple(
            self._chunks.get(identifier) or self._rehydrate(identifier, text, data)
            for identifier, text, data, distance in matches
            if score_threshold is None or float(distance) <= score_threshold
        )

    @staticmethod
    def _metadata(chunk: KnowledgeChunk) -> dict[str, object]:
        data = chunk.metadata
        return {"document_id": chunk.document_id, "document_name": data.document_name, "authority": data.authority, "agency": data.agency or "", "document_type": data.document_type, "publication_year": data.publication_year or 0, "page_number": data.page_number, "section": data.section or "", "heading": data.heading or "", "district": data.district or "", "river": data.river or "", "hazard_type": data.hazard_type or "", "keywords": ",".join(data.keywords), "language": data.language, "source_path": data.source_path or ""}

    @staticmethod
    def _rehydrate(identifier: str, text: str, data: Mapping[str, object]) -> KnowledgeChunk:
        return KnowledgeChunk(identifier, str(data["document_id"]), text, ChunkMetadata(
            document_name=str(data["document_name"]), authority=str(data["authority"]),
            agency=str(data.get("agency") or "") or None, document_type=str(data["document_type"]),
            publication_year=(int(data["publication_year"]) if int(data.get("publication_year") or 0) > 0 else None), page_number=int(data["page_number"]),
            section=str(data.get("section") or "") or None, heading=str(data.get("heading") or "") or None,
            district=str(data.get("district") or "") or None, river=str(data.get("river") or "") or None,
            hazard_type=str(data.get("hazard_type") or "") or None,
            keywords=tuple(value for value in str(data.get("keywords") or "").split(",") if value),
            language=str(data.get("language") or "en"), source_path=str(data.get("source_path") or "") or None,
        ))
