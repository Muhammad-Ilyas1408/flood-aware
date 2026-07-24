"""Evidence context assembly with provenance and deterministic deduplication."""

from backend.app.rag.models import Citation, EvidenceContext, KnowledgeChunk


class ContextBuilder:
    """Build bounded evidence context without changing source passage text."""

    def __init__(self, max_characters: int = 12000) -> None:
        self._max_characters = max_characters

    def build(self, chunks: tuple[KnowledgeChunk, ...]) -> EvidenceContext:
        """Deduplicate by chunk identity while preserving retrieval order."""

        selected: list[KnowledgeChunk] = []
        seen: set[str] = set()
        total = 0
        for chunk in chunks:
            if chunk.chunk_id in seen or total + len(chunk.text) > self._max_characters:
                continue
            seen.add(chunk.chunk_id)
            selected.append(chunk)
            total += len(chunk.text)
        citations = tuple(Citation(c.metadata.document_name, c.metadata.page_number, c.metadata.section) for c in selected)
        text = "\n\n".join(f"[{citation.document_name}, p. {citation.page_number}]\n{chunk.text}" for chunk, citation in zip(selected, citations, strict=True))
        return EvidenceContext(text, tuple(selected), citations)
