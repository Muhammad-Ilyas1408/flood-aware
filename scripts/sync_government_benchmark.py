"""Synchronize benchmark retrieval metadata with the persisted government index."""

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.embedding_service import OpenAIEmbeddingService
from backend.app.rag.retriever import GovernmentRetriever
from backend.app.rag.settings import GovernmentKnowledgeSettings
from backend.app.rag.vector_store import ChromaVectorStore


_LOGGER = logging.getLogger(__name__)


def synchronize(benchmark_path: str | Path) -> tuple[int, int, int]:
    """Refresh machine-maintained retrieval fields while preserving authored metadata."""

    source = Path(benchmark_path)
    payload = _load_benchmark(source)
    settings = GovernmentKnowledgeSettings()
    embeddings = OpenAIEmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )
    store = ChromaVectorStore(settings.chroma_directory, settings.collection_name)
    retriever = GovernmentRetriever(embeddings, store)
    questions = payload["questions"]
    assert isinstance(questions, list)
    chunk_total = 0
    citation_total = 0
    try:
        print("Synchronizing benchmark...")
        for question in questions:
            identifier, text = _question_identity(question)
            chunks = retriever.retrieve(text, settings.maximum_retrieved_chunks)
            question["relevant_chunk_ids"] = [chunk.chunk_id for chunk in chunks]
            question["expected_citations"] = [
                {
                    "document_name": chunk.metadata.document_name,
                    "page_number": chunk.metadata.page_number,
                    "section": chunk.metadata.section,
                }
                for chunk in chunks
            ]
            chunk_total += len(chunks)
            citation_total += len(chunks)
            print(
                f"Question: {identifier}\n"
                f"Retrieved chunks: {len(chunks)}\n"
                f"Updated chunk ids: {len(chunks)}\n"
                f"Updated citations: {len(chunks)}"
            )
        source.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    finally:
        store.close()
    return len(questions), chunk_total, citation_total


def main(arguments: list[str] | None = None) -> int:
    """Run benchmark synchronization and return a CI-friendly exit status."""

    parser = argparse.ArgumentParser(
        description="Synchronize Government Knowledge Engine benchmark metadata."
    )
    parser.add_argument(
        "--benchmark",
        default="data/knowledge/benchmarks/government_questions.json",
        help="Path to the benchmark JSON file to update in place.",
    )
    options = parser.parse_args(arguments)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        questions, chunks, citations = synchronize(options.benchmark)
    except Exception as error:
        _LOGGER.error("Benchmark synchronization failed: %s", error)
        return 1
    print(
        "Benchmark synchronization complete.\n"
        f"Questions updated: {questions}\n"
        f"Chunks written: {chunks}\n"
        f"Citations written: {citations}"
    )
    return 0


def _load_benchmark(source: Path) -> dict[str, object]:
    """Load the benchmark JSON without rebuilding its human-authored metadata."""

    if not source.is_file():
        raise ValueError(f"Benchmark file does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Benchmark JSON is invalid: {source}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise ValueError("Benchmark requires a top-level 'questions' array.")
    return payload


def _question_identity(question: object) -> tuple[str, str]:
    """Validate only the fields needed to execute a benchmark retrieval."""

    if not isinstance(question, dict):
        raise ValueError("Each benchmark question must be an object.")
    identifier = question.get("id")
    text = question.get("question")
    if not isinstance(identifier, str) or not identifier or not isinstance(text, str) or not text:
        raise ValueError("Each benchmark question requires non-blank 'id' and 'question'.")
    return identifier, text


if __name__ == "__main__":
    raise SystemExit(main())
