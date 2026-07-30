"""Production-facing tests for the Government Disaster Knowledge Engine."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.government_loader import GovernmentLoader
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.models import ChunkMetadata, KnowledgeChunk
from backend.app.rag.pdf_cleaner import PDFCleaner
from backend.app.rag.prompt_builder import PromptBuilder
from backend.app.rag.protocols import EmbeddingService, ResponseGenerator, VectorStore
from backend.app.rag.retriever import GovernmentRetriever
from backend.app.rag.semantic_chunker import SemanticChunker
from backend.app.rag.vector_store import ChromaVectorStore


def _chunk(
    identifier: str, text: str = "Flood preparedness guidance."
) -> KnowledgeChunk:
    """Build one authoritative evidence passage for isolated tests."""

    return KnowledgeChunk(
        identifier,
        "ndma-plan",
        text,
        ChunkMetadata(
            document_name="NDMA Plan",
            authority="NDMA",
            agency="NDMA",
            document_type="National plan",
            publication_year=None,
            page_number=4,
            section="Preparedness",
            heading="Preparedness",
        ),
    )


class FakeEmbeddings(EmbeddingService):
    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((float(len(text)),) for text in texts)


class FakeStore(VectorStore):
    def __init__(
        self,
        chunks: tuple[KnowledgeChunk, ...],
        distances: tuple[float, ...] | None = None,
    ) -> None:
        self.chunks = chunks
        self.distances = distances if distances is not None else (0.0,) * len(chunks)
        self.calls: list[tuple[tuple[float, ...], int, object]] = []

    def index(
        self, chunks: tuple[KnowledgeChunk, ...], vectors: tuple[tuple[float, ...], ...]
    ) -> None:
        self.chunks = chunks

    def search(
        self,
        vector: tuple[float, ...],
        top_k: int,
        filters: object = None,
        score_threshold: float | None = None,
    ) -> tuple[KnowledgeChunk, ...]:
        self.calls.append((vector, top_k, filters))
        nearest = sorted(zip(self.chunks, self.distances), key=lambda pair: pair[1])
        return tuple(
            chunk
            for chunk, distance in nearest[:top_k]
            if score_threshold is None or distance <= score_threshold
        )


class FakeGenerator(ResponseGenerator):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "Use the preparedness guidance."


class GovernmentKnowledgeEngineTests(unittest.TestCase):
    def test_semantic_chunking_preserves_heading_page_and_provenance(self) -> None:
        from backend.app.rag.models import (
            KnowledgeDocument,
            KnowledgeMetadata,
            KnowledgePage,
        )

        document = KnowledgeDocument(
            "swat",
            "Swat Risk Map.pdf",
            Path("Swat Risk Map.pdf"),
            (
                KnowledgePage(
                    1, "1. FLOOD RISK\n\nFlood preparedness protects communities."
                ),
            ),
            KnowledgeMetadata("NDMA", "Risk mapping"),
        )
        chunks = SemanticChunker().chunk(document)
        self.assertEqual(chunks[0].metadata.page_number, 1)
        self.assertEqual(chunks[0].metadata.heading, "1. FLOOD RISK")
        self.assertEqual(chunks[0].metadata.document_name, "Swat Risk Map.pdf")

    def test_semantic_chunker_rejects_numeric_table_rows_as_headings(self) -> None:
        """Tabular values must not overwrite the current section provenance."""
        chunker = SemanticChunker()

        self.assertFalse(chunker._is_heading("450.00 Lai Nullah"))
        self.assertFalse(
            chunker._is_heading("450.00 Lai Nullah\n6,125.00\n8,698.00")
        )

    def test_semantic_chunker_retains_valid_numbered_and_uppercase_headings(self) -> None:
        """Section markers and existing uppercase headings remain recognized."""
        chunker = SemanticChunker()

        for heading in (
            "1. Introduction",
            "3.2 Evacuation Procedures",
            "12) Overview",
            "FLOOD RISK",
        ):
            with self.subTest(heading=heading):
                self.assertTrue(chunker._is_heading(heading))

    def test_context_deduplicates_and_retains_citations(self) -> None:
        chunk = _chunk("one")
        context = ContextBuilder().build((chunk, chunk))
        self.assertEqual(context.chunks, (chunk,))
        self.assertEqual(context.citations[0].document_name, "NDMA Plan")
        self.assertIn("p. 4", context.text)

    def test_context_deduplicates_near_identical_text_across_chunk_ids(self) -> None:
        """Boilerplate text repeated under a different chunk_id is still collapsed."""
        first = _chunk("page-3", "  MESSAGE FROM SECRETARY   RELIEF REHABILITATION.\n\n")
        duplicate = _chunk("page-9", "message from secretary relief rehabilitation.")

        context = ContextBuilder().build((first, duplicate))

        self.assertEqual(context.chunks, (first,))

    def test_knowledge_tool_runs_grounded_pipeline_with_citations(self) -> None:
        store = FakeStore((_chunk("one"),))
        generator = FakeGenerator()
        tool = KnowledgeTool(
            GovernmentRetriever(FakeEmbeddings(), store),
            ContextBuilder(),
            PromptBuilder(),
            generator,
        )
        answer = tool.answer("How should communities prepare?")
        self.assertEqual(answer.text, "Use the preparedness guidance.")
        self.assertEqual(answer.citations[0].page_number, 4)
        self.assertEqual(store.calls[0][1], 5)
        self.assertIn("Government evidence", generator.calls[0][1])

    def test_knowledge_tool_threads_score_threshold_to_retrieval(self) -> None:
        """A configured score_threshold filters weak matches before generation."""
        strong = _chunk("strong", "Detailed flood embankment maintenance policy.")
        weak = _chunk(
            "weak", "MESSAGE FROM SECRETARY RELIEF REHABILITATION SETTLEMENT."
        )
        store = FakeStore((strong, weak), distances=(0.4, 1.9))
        generator = FakeGenerator()
        tool = KnowledgeTool(
            GovernmentRetriever(FakeEmbeddings(), store),
            ContextBuilder(),
            PromptBuilder(),
            generator,
            score_threshold=1.3,
        )

        answer = tool.answer("What is the government policy about flood?")

        self.assertEqual(len(answer.citations), 1)
        self.assertEqual(answer.citations[0].document_name, "NDMA Plan")
        self.assertIn("Detailed flood embankment", generator.calls[0][1])

    def test_knowledge_tool_reports_honest_absence_above_threshold(self) -> None:
        """No chunk clears the threshold: an honest no-guidance answer, no generation."""
        weak = _chunk(
            "weak", "MESSAGE FROM SECRETARY RELIEF REHABILITATION SETTLEMENT."
        )
        store = FakeStore((weak,), distances=(1.9,))
        generator = FakeGenerator()
        tool = KnowledgeTool(
            GovernmentRetriever(FakeEmbeddings(), store),
            ContextBuilder(),
            PromptBuilder(),
            generator,
            score_threshold=1.3,
        )

        answer = tool.answer("What is the government policy about flood?")

        self.assertEqual(answer.citations, ())
        self.assertEqual(generator.calls, [])
        self.assertIn("No sufficiently relevant", answer.text)

    @unittest.skipUnless(
        importlib.util.find_spec("chromadb"), "ChromaDB is not installed."
    )
    @unittest.skipIf(
        os.name == "nt", "ChromaDB retains HNSW files on Windows until process exit."
    )
    def test_vector_store_score_threshold_filters_weak_matches(self) -> None:
        """A real Chroma collection filters chunks beyond the configured distance."""
        near = _chunk("near")
        far = _chunk("far")
        with tempfile.TemporaryDirectory() as directory:
            store = ChromaVectorStore(directory, "threshold-test")
            store.index((near, far), ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)))

            unfiltered = store.search((1.0, 0.0, 0.0), 2)
            filtered = store.search((1.0, 0.0, 0.0), 2, score_threshold=1.0)
            store.close()

        self.assertEqual(set(unfiltered), {near, far})
        self.assertEqual(filtered, (near,))

    @unittest.skipUnless(importlib.util.find_spec("fitz"), "PyMuPDF is not installed.")
    def test_loader_builds_real_authoritative_corpus(self) -> None:
        """Configured government PDFs load into an immutable multi-document corpus."""

        corpus = GovernmentLoader().load_corpus(Path("data/knowledge/raw"))
        self.assertEqual(len(corpus.documents), 4)
        self.assertTrue(all(document.pages for document in corpus.documents))

    @unittest.skipUnless(
        importlib.util.find_spec("chromadb"), "ChromaDB is not installed."
    )
    @unittest.skipIf(
        os.name == "nt", "ChromaDB retains HNSW files on Windows until process exit."
    )
    def test_persistent_index_rehydrates_chunks_after_store_restart(self) -> None:
        """A fresh store instance retrieves a persisted canonical chunk."""

        chunk = _chunk("persistent")
        with tempfile.TemporaryDirectory() as directory:
            initial_store = ChromaVectorStore(directory, "persistence-test")
            initial_store.index((chunk,), ((1.0, 0.0),))
            initial_store.close()
            restarted_store = ChromaVectorStore(directory, "persistence-test")
            retrieved = restarted_store.search((1.0, 0.0), 1)
            restarted_store.close()

        self.assertEqual(retrieved, (chunk,))
