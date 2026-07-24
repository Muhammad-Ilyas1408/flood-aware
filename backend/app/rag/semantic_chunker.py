"""Section-aware semantic chunking for government disaster documents."""

from hashlib import sha256
import re

from backend.app.rag.models import ChunkMetadata, KnowledgeChunk, KnowledgeDocument


class SemanticChunker:
    """Chunk paragraphs by headings and page boundaries without fixed-width splitting."""

    def __init__(self, max_characters: int = 1800) -> None:
        self._max_characters = max_characters

    def chunk(self, document: KnowledgeDocument) -> tuple[KnowledgeChunk, ...]:
        """Create ordered semantic passages retaining page and heading provenance."""

        chunks: list[KnowledgeChunk] = []
        heading = None
        for page in document.pages:
            for paragraph in filter(None, re.split(r"\n\s*\n", page.text)):
                candidate = paragraph.strip()
                if self._is_heading(candidate):
                    heading = candidate
                    continue
                for text in self._split_paragraph(candidate):
                    index = len(chunks)
                    identifier = sha256(f"{document.document_id}|{page.page_number}|{index}|{text}".encode()).hexdigest()
                    chunks.append(KnowledgeChunk(identifier, document.document_id, text, ChunkMetadata(
                        document_name=document.name, authority=document.metadata.authority,
                        agency=document.metadata.authority, document_type=document.metadata.document_type,
                        publication_year=None, page_number=page.page_number, section=heading,
                        heading=heading, keywords=tuple(sorted(set(re.findall(r"[A-Za-z]{5,}", text.lower()))))[:12],
                        source_path=str(document.source_path),
                    )))
        return tuple(chunks)

    def _split_paragraph(self, paragraph: str) -> tuple[str, ...]:
        if len(paragraph) <= self._max_characters:
            return (paragraph,)
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            if current and len(current) + len(sentence) + 1 > self._max_characters:
                parts.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            parts.append(current)
        return tuple(parts)

    @staticmethod
    def _is_heading(text: str) -> bool:
        return len(text) <= 160 and (text.isupper() or bool(re.match(r"^\d+(?:\.\d+)*[.)]?\s+", text)))
