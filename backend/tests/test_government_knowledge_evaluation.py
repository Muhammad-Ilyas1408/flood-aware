"""Tests for isolated Government Knowledge Engine production validation."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.evaluation.benchmark_loader import BenchmarkLoader
from backend.app.rag.evaluation.citation_checker import evaluate_citations
from backend.app.rag.evaluation.evaluation_report import EvaluationReportWriter
from backend.app.rag.evaluation.evaluation_runner import EvaluationRunner
from backend.app.rag.evaluation.metrics_aggregator import MetricsAggregator
from backend.app.rag.evaluation.retrieval_metrics import evaluate_retrieval
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.models import ChunkMetadata, Citation, GroundedAnswer, KnowledgeChunk
from backend.app.rag.prompt_builder import PromptBuilder
from backend.app.rag.protocols import EmbeddingService, ResponseGenerator, VectorStore
from backend.app.rag.retriever import GovernmentRetriever
from scripts import evaluate_government_knowledge as evaluation_cli


def _chunk(identifier: str, document: str = "NDMA Plan.pdf") -> KnowledgeChunk:
    return KnowledgeChunk(
        identifier,
        "ndma-plan",
        "Government guidance recommends flood preparedness.",
        ChunkMetadata(document, "NDMA", "NDMA", "National plan", 2025, 4, "Preparedness"),
    )


class _Embeddings(EmbeddingService):
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((1.0,) for _ in texts)


class _Store(VectorStore):
    def __init__(self, chunks: tuple[KnowledgeChunk, ...]) -> None:
        self._chunks = chunks

    def index(self, chunks: tuple[KnowledgeChunk, ...], vectors: tuple[tuple[float, ...], ...]) -> None:
        self._chunks = chunks

    def search(self, vector: tuple[float, ...], top_k: int, filters=None, score_threshold=None) -> tuple[KnowledgeChunk, ...]:
        return self._chunks[:top_k]


class _Generator(ResponseGenerator):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "Government guidance recommends flood preparedness."


class _ClosableStore:
    def close(self) -> None:
        pass


class GovernmentKnowledgeEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunk = _chunk("chunk-1")
        self.chunks = (self.chunk, _chunk("chunk-2", "PDMA Plan.pdf"))

    def test_retrieval_metrics_separate_chunk_and_document_relevance(self) -> None:
        metrics = evaluate_retrieval(self.chunks, ("chunk-1",), ("NDMA Plan.pdf",))
        self.assertEqual(metrics["chunk_precision_at_k"], 0.5)
        self.assertEqual(metrics["chunk_recall_at_k"], 1.0)
        self.assertEqual(metrics["document_precision_at_k"], 0.5)
        self.assertEqual(metrics["document_recall_at_k"], 1.0)
        self.assertEqual(metrics["hit_rate"], 1.0)
        self.assertEqual(metrics["mrr"], 1.0)

    def test_citation_checker_rejects_citations_not_in_retrieved_evidence(self) -> None:
        valid = evaluate_citations(
            GroundedAnswer("Answer", (Citation("NDMA Plan.pdf", 4, "Preparedness"),)),
            (self.chunk,),
        )
        invalid = evaluate_citations(
            GroundedAnswer("Answer", (Citation("Unknown.pdf", 99, None),)),
            (self.chunk,),
        )
        self.assertEqual(valid["citation_accuracy"], 1.0)
        self.assertEqual(invalid["invalid_citation_rate"], 1.0)

    def test_benchmark_loader_handles_optional_metadata_and_old_schema(self) -> None:
        benchmark = {
            "questions": [
                {"id": "old", "question": "Old schema?"},
                {
                    "id": "new",
                    "question": "New schema?",
                    "difficulty": "hard",
                    "category": "preparedness",
                    "hazard": "flood",
                    "agency": "NDMA",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.json"
            path.write_text(json.dumps(benchmark), encoding="utf-8")
            loaded = BenchmarkLoader().load(path)
        self.assertIsNone(loaded[0]["difficulty"])
        self.assertEqual(loaded[1]["agency"], "NDMA")

    def test_aggregator_produces_warnings_without_runtime_dependencies(self) -> None:
        record = {
            "retrieval_metrics": {"hit_rate": 0.0},
            "citation_metrics": {
                "invalid_citation_rate": 0.0,
                "missing_citation_rate": 0.0,
            },
            "expected_citations_present": True,
        }
        summary = MetricsAggregator().aggregate((record,))
        self.assertEqual(summary["benchmark_count"], 1)
        self.assertTrue(summary["warnings"])

    def test_runner_and_report_writer(self) -> None:
        retriever = GovernmentRetriever(_Embeddings(), _Store((self.chunk,)))
        tool = KnowledgeTool(retriever, ContextBuilder(), PromptBuilder(), _Generator())
        benchmark = {
            "questions": [{
                "id": "preparedness",
                "question": "What does the government recommend?",
                "relevant_chunk_ids": ["chunk-1"],
                "relevant_documents": ["NDMA Plan.pdf"],
                "expected_citations": [{
                    "document_name": "NDMA Plan.pdf", "page_number": 4, "section": "Preparedness"
                }],
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.json"
            path.write_text(json.dumps(benchmark), encoding="utf-8")
            summary = EvaluationRunner(tool, retriever.retrieve).run(path)
            json_path, markdown_path = EvaluationReportWriter().write(summary, directory)
            self.assertTrue(summary["pass"])
            self.assertEqual(json_path.name, "evaluation.json")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["benchmark_count"], 1)
            self.assertIn("chunk_precision_at_k", markdown_path.read_text(encoding="utf-8"))

    def test_cli_returns_success_with_injected_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            benchmark = Path(directory) / "benchmark.json"
            benchmark.write_text(json.dumps({"questions": [{"id": "q", "question": "Q?"}]}), encoding="utf-8")
            summary = {
                "benchmark_count": 1,
                "retrieval_metrics": {},
                "citation_metrics": {},
                "warnings": (),
                "pass": True,
                "records": (),
            }
            runner = unittest.mock.Mock()
            runner.run.return_value = summary
            with patch.object(evaluation_cli, "build_runner", return_value=(runner, _ClosableStore())):
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    code = evaluation_cli.main(["--benchmark", str(benchmark), "--output-directory", directory])
            self.assertEqual(code, 0)
            self.assertIn("Evaluation passed", output.getvalue())
