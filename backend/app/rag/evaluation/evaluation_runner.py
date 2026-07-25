"""Orchestrate lightweight Government Knowledge Engine evaluation."""

import logging
from collections.abc import Callable
from pathlib import Path

from backend.app.rag.evaluation.benchmark_loader import BenchmarkLoader
from backend.app.rag.evaluation.citation_checker import evaluate_citations
from backend.app.rag.evaluation.metrics_aggregator import MetricsAggregator
from backend.app.rag.evaluation.retrieval_metrics import evaluate_retrieval
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.models import Citation, KnowledgeChunk

_LOGGER = logging.getLogger(__name__)
Retriever = Callable[[str, int], tuple[KnowledgeChunk, ...]]


class EvaluationRunner:
    """Coordinate benchmark execution without parsing, aggregation, or reporting logic."""

    def __init__(
        self,
        knowledge_tool: KnowledgeTool,
        retrieve: Retriever,
        benchmark_loader: BenchmarkLoader | None = None,
        metrics_aggregator: MetricsAggregator | None = None,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError("Evaluation top_k must be positive.")
        self._knowledge_tool = knowledge_tool
        self._retrieve = retrieve
        self._benchmark_loader = benchmark_loader or BenchmarkLoader()
        self._metrics_aggregator = metrics_aggregator or MetricsAggregator()
        self._top_k = top_k

    def run(self, benchmark_path: str | Path) -> dict[str, object]:
        """Evaluate the supplied benchmark with the public production interfaces."""

        questions = self._benchmark_loader.load(benchmark_path)
        _LOGGER.info("Evaluation started: question_count=%s", len(questions))
        records = tuple(self._evaluate(question) for question in questions)
        summary = self._metrics_aggregator.aggregate(records)
        summary["pass"] = not summary["warnings"]
        summary["records"] = records
        _LOGGER.info("Evaluation finished: questions_evaluated=%s", len(records))
        return summary

    def _evaluate(self, question: dict[str, object]) -> dict[str, object]:
        text = question["question"]
        assert isinstance(text, str)
        chunks = self._retrieve(text, self._top_k)
        answer = self._knowledge_tool.answer(text, self._top_k)
        return {
            "id": question["id"],
            "question": text,
            "retrieval_metrics": evaluate_retrieval(
                chunks,
                tuple(question["relevant_chunk_ids"]),
                tuple(question["relevant_documents"]),
            ),
            "citation_metrics": evaluate_citations(answer, chunks),
            "expected_citations_present": self._expected_citations_present(
                answer.citations, tuple(question["expected_citations"])
            ),
        }

    @staticmethod
    def _expected_citations_present(
        citations: tuple[Citation, ...], expected: tuple[object, ...]
    ) -> bool:
        """Check benchmark-required citations without altering citation integrity metrics."""

        present = {
            (item.document_name, item.page_number, item.section) for item in citations
        }
        return all(item in present for item in expected)
