"""Evidence context assembly with provenance and deterministic deduplication."""

import re

from backend.app.rag.models import Citation, EvidenceContext, KnowledgeChunk

_WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Fold whitespace and case so near-identical passages compare equal."""

    return _WHITESPACE_PATTERN.sub(" ", text).strip().lower()


class ContextBuilder:
    """Build bounded evidence context without changing source passage text."""

    def __init__(self, max_characters: int = 12000) -> None:
        self._max_characters = max_characters

    def build(self, chunks: tuple[KnowledgeChunk, ...]) -> EvidenceContext:
        """Deduplicate by chunk identity and normalized text, preserving order.

        Repeated boilerplate (e.g. a preamble page re-chunked under a different
        chunk_id) can otherwise survive chunk_id-only deduplication as if it
        were independent evidence.
        """

        selected: list[KnowledgeChunk] = []
        seen_ids: set[str] = set()
        seen_text: set[str] = set()
        total = 0
        for chunk in chunks:
            normalized = _normalize_text(chunk.text)
            if (
                chunk.chunk_id in seen_ids
                or normalized in seen_text
                or total + len(chunk.text) > self._max_characters
            ):
                continue
            seen_ids.add(chunk.chunk_id)
            seen_text.add(normalized)
            selected.append(chunk)
            total += len(chunk.text)
        citations = tuple(
            Citation(
                c.metadata.document_name, c.metadata.page_number, c.metadata.section
            )
            for c in selected
        )
        text = "\n\n".join(
            f"[{citation.document_name}, p. {citation.page_number}]\n{chunk.text}"
            for chunk, citation in zip(selected, citations, strict=True)
        )
        return EvidenceContext(text, tuple(selected), citations)
