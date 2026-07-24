"""Run Government Knowledge Engine validation for local use or CI."""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.embedding_service import OpenAIEmbeddingService
from backend.app.rag.evaluation.evaluation_report import EvaluationReportWriter
from backend.app.rag.evaluation.evaluation_runner import EvaluationRunner
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.prompt_builder import PromptBuilder
from backend.app.rag.response_generator import OpenAIResponseGenerator
from backend.app.rag.retriever import GovernmentRetriever
from backend.app.rag.settings import GovernmentKnowledgeSettings
from backend.app.rag.vector_store import ChromaVectorStore


_LOGGER = logging.getLogger(__name__)


def build_runner(settings: GovernmentKnowledgeSettings) -> tuple[EvaluationRunner, ChromaVectorStore]:
    """Compose existing production components externally for an evaluation run."""

    embeddings = OpenAIEmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )
    store = ChromaVectorStore(settings.chroma_directory, settings.collection_name)
    retriever = GovernmentRetriever(embeddings, store)
    tool = KnowledgeTool(
        retriever,
        ContextBuilder(settings.context_max_characters),
        PromptBuilder(),
        OpenAIResponseGenerator(
            api_key=settings.openai_api_key,
            model=settings.response_model,
        ),
    )
    return EvaluationRunner(tool, retriever.retrieve, top_k=settings.maximum_retrieved_chunks), store


def main(arguments: list[str] | None = None) -> int:
    """Execute evaluation, print a concise summary, and return a CI-friendly status."""

    parser = argparse.ArgumentParser(description="Evaluate the Government Knowledge Engine.")
    parser.add_argument(
        "--benchmark",
        default="data/knowledge/benchmarks/government_questions.json",
        help="Path to the benchmark JSON file.",
    )
    parser.add_argument(
        "--output-directory",
        default="data/outputs/evaluation",
        help="Directory for evaluation.json and evaluation.md.",
    )
    options = parser.parse_args(arguments)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    store: ChromaVectorStore | None = None
    try:
        runner, store = build_runner(GovernmentKnowledgeSettings())
        summary = runner.run(options.benchmark)
        json_path, markdown_path = EvaluationReportWriter().write(summary, options.output_directory)
        _LOGGER.info("Warnings: %s", len(summary["warnings"]))
        print(
            f"Evaluation {'passed' if summary['pass'] else 'failed'}: "
            f"questions={summary['benchmark_count']} json={json_path} markdown={markdown_path}"
        )
        return 0 if summary["pass"] else 1
    except Exception as error:
        _LOGGER.error("Evaluation failed: %s", error)
        return 2
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
