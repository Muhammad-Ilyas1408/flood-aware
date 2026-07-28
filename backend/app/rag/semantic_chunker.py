"""Section-aware semantic chunking for government disaster documents."""

import re
from hashlib import sha256

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
                    identifier = sha256(
                        f"{document.document_id}|{page.page_number}|{index}|{text}".encode()
                    ).hexdigest()
                    chunks.append(
                        KnowledgeChunk(
                            identifier,
                            document.document_id,
                            text,
                            ChunkMetadata(
                                document_name=document.name,
                                authority=document.metadata.authority,
                                agency=document.metadata.authority,
                                document_type=document.metadata.document_type,
                                publication_year=None,
                                page_number=page.page_number,
                                section=heading,
                                heading=heading,
                                keywords=tuple(
                                    sorted(
                                        set(re.findall(r"[A-Za-z]{5,}", text.lower()))
                                    )
                                )[:12],
                                source_path=str(document.source_path),
                            ),
                        )
                    )
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
        if len(text) > 160:
            return False
        if text.isupper():
            return True

        match = re.match(r"^(\d+(?:\.\d+)*[.)]?)\s+", text)
        if match is None:
            return False

        section_parts = match.group(1).rstrip(".)").split(".")
        numeric_tokens = set(re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", text))
        return (
            len(numeric_tokens) == 1
            and len(section_parts[0]) <= 2
            and all(
                len(part) == 1 or not part.startswith("0")
                for part in section_parts[1:]
            )
            and bool(re.search(r"[A-Za-z]", text[match.end() :]))
        )
