"""Immutable domain models for the Government Disaster Knowledge Engine."""

from dataclasses import dataclass
from pathlib import Path

from backend.app.rag.exceptions import KnowledgeDocumentError


@dataclass(frozen=True, slots=True)
class KnowledgeMetadata:
    """Describe authoritative provenance for a government source document."""

    authority: str
    document_type: str


@dataclass(frozen=True, slots=True)
class KnowledgePage:
    """Represent unmodified extracted text for one one-based PDF page."""

    page_number: int
    text: str

    def __post_init__(self) -> None:
        if self.page_number < 1 or not isinstance(self.text, str):
            raise KnowledgeDocumentError(
                "Knowledge pages require a valid number and text."
            )


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """Represent an authoritative PDF and its page-preserving extracted content."""

    document_id: str
    name: str
    source_path: Path
    pages: tuple[KnowledgePage, ...]
    metadata: KnowledgeMetadata

    def __post_init__(self) -> None:
        if (
            not self.document_id
            or not self.name
            or not isinstance(self.source_path, Path)
        ):
            raise KnowledgeDocumentError("Knowledge document identity is invalid.")
        if not isinstance(self.metadata, KnowledgeMetadata):
            raise KnowledgeDocumentError("Knowledge document metadata is invalid.")
        if any(not isinstance(page, KnowledgePage) for page in self.pages):
            raise KnowledgeDocumentError("Knowledge document pages are invalid.")


@dataclass(frozen=True, slots=True)
class GovernmentCorpus:
    """Immutable validated collection of authoritative government documents."""

    documents: tuple[KnowledgeDocument, ...]

    def __post_init__(self) -> None:
        if not self.documents or any(
            not isinstance(document, KnowledgeDocument) for document in self.documents
        ):
            raise KnowledgeDocumentError("Government corpus requires source documents.")
        identifiers = tuple(document.document_id for document in self.documents)
        if len(identifiers) != len(set(identifiers)):
            raise KnowledgeDocumentError(
                "Government corpus document identifiers must be unique."
            )


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Metadata used for source attribution and government-document filtering."""

    document_name: str
    authority: str
    agency: str | None
    document_type: str
    publication_year: int | None
    page_number: int
    section: str | None = None
    heading: str | None = None
    district: str | None = None
    river: str | None = None
    hazard_type: str | None = None
    keywords: tuple[str, ...] = ()
    language: str = "en"
    source_path: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """One semantic government-document passage with durable source provenance."""

    chunk_id: str
    document_id: str
    text: str
    metadata: ChunkMetadata

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.document_id or not self.text.strip():
            raise KnowledgeDocumentError("Knowledge chunks require identity and text.")
        if not isinstance(self.metadata, ChunkMetadata):
            raise KnowledgeDocumentError("Knowledge chunk metadata is invalid.")


@dataclass(frozen=True, slots=True)
class Citation:
    """One human-readable reference to authoritative retrieved evidence."""

    document_name: str
    page_number: int
    section: str | None


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    """Deduplicated evidence and citations ready for grounded answer generation."""

    text: str
    chunks: tuple[KnowledgeChunk, ...]
    citations: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    """A generated answer accompanied by the evidence citations used to ground it."""

    text: str
    citations: tuple[Citation, ...]
