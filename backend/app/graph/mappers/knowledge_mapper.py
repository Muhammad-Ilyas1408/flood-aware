"""Map grounded government-knowledge citations into graph evidence."""

from backend.app.graph.state import KnowledgeEvidence
from backend.app.rag.models import GroundedAnswer


class KnowledgeEvidenceMapper:
    """Retain authoritative citations without interpreting generated answer text."""

    @staticmethod
    def to_graph(answer: GroundedAnswer) -> KnowledgeEvidence:
        """Return citation evidence in stable document, page, and section order."""
        citations = tuple(
            _citation_text(
                citation.document_name, citation.page_number, citation.section
            )
            for citation in answer.citations
        )
        return KnowledgeEvidence(citations=citations)


def _citation_text(document_name: str, page_number: int, section: str | None) -> str:
    """Format one existing citation without adding or altering its provenance."""
    value = f"{document_name}:p{page_number}"
    return f"{value}:{section}" if section is not None else value
