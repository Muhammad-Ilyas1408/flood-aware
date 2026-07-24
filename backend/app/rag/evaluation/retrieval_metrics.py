"""Standard chunk-level and document-level information-retrieval metrics."""

from backend.app.rag.models import KnowledgeChunk


def evaluate_retrieval(
    chunks: tuple[KnowledgeChunk, ...],
    relevant_chunk_ids: tuple[str, ...],
    relevant_documents: tuple[str, ...],
) -> dict[str, float]:
    """Calculate independent chunk/document metrics plus Hit Rate and MRR."""

    retrieved_chunk_ids = tuple(chunk.chunk_id for chunk in chunks)
    retrieved_documents = tuple(chunk.metadata.document_name for chunk in chunks)
    expected_chunks = set(relevant_chunk_ids)
    expected_documents = set(relevant_documents)
    chunk_matches = [identifier for identifier in retrieved_chunk_ids if identifier in expected_chunks]
    unique_retrieved_documents = set(retrieved_documents)
    document_matches = unique_retrieved_documents & expected_documents
    first_relevant_rank = next(
        (
            index
            for index, chunk in enumerate(chunks, start=1)
            if chunk.chunk_id in expected_chunks
            or chunk.metadata.document_name in expected_documents
        ),
        None,
    )
    return {
        "chunk_precision_at_k": _ratio(len(chunk_matches), len(chunks)),
        "chunk_recall_at_k": _ratio(len(set(chunk_matches)), len(expected_chunks)),
        "document_precision_at_k": _ratio(
            len(document_matches), len(unique_retrieved_documents)
        ),
        "document_recall_at_k": _ratio(len(document_matches), len(expected_documents)),
        "hit_rate": float(first_relevant_rank is not None),
        "mrr": 1.0 / first_relevant_rank if first_relevant_rank else 0.0,
        "retrieved_chunk_count": float(len(chunks)),
    }


def _ratio(numerator: int, denominator: int) -> float:
    """Return zero when an expectation is intentionally absent from a benchmark."""

    return numerator / denominator if denominator else 0.0
