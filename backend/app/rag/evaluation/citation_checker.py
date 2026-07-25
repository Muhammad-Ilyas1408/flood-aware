"""Factual citation integrity checks against retrieved canonical evidence."""

from backend.app.rag.models import Citation, GroundedAnswer, KnowledgeChunk


def evaluate_citations(
    answer: GroundedAnswer,
    chunks: tuple[KnowledgeChunk, ...],
) -> dict[str, float]:
    """Measure whether citations refer to an exact retrieved document and page."""

    valid = {_citation(chunk) for chunk in chunks}
    citations = answer.citations
    valid_count = sum(citation in valid for citation in citations)
    citation_count = len(citations)
    return {
        "citation_coverage": float(bool(citations)) if answer.text.strip() else 1.0,
        "missing_citation_rate": float(not citations) if answer.text.strip() else 0.0,
        "invalid_citation_rate": (
            (citation_count - valid_count) / citation_count if citation_count else 0.0
        ),
        "citation_accuracy": valid_count / citation_count if citation_count else 0.0,
    }


def _citation(chunk: KnowledgeChunk) -> Citation:
    return Citation(
        document_name=chunk.metadata.document_name,
        page_number=chunk.metadata.page_number,
        section=chunk.metadata.section,
    )
