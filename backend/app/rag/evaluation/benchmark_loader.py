"""Load and validate lightweight Government Knowledge Engine benchmarks."""

import json
import logging
from pathlib import Path


_LOGGER = logging.getLogger(__name__)
_DIFFICULTIES = frozenset({"easy", "medium", "hard"})
_OPTIONAL_METADATA = ("category", "hazard", "agency")


class BenchmarkLoader:
    """Read benchmark questions without coupling them to production RAG models."""

    def load(self, path: str | Path) -> tuple[dict[str, object], ...]:
        """Return validated benchmark question dictionaries from a JSON document."""

        source = Path(path)
        if not source.is_file():
            raise ValueError(f"Benchmark file does not exist: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Benchmark JSON is invalid: {source}") from error
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(questions, list) or not questions:
            raise ValueError("Benchmark requires a non-empty 'questions' array.")
        loaded = tuple(self._validate_question(question) for question in questions)
        _LOGGER.info("Benchmark loaded: question_count=%s path=%s", len(loaded), source)
        return loaded

    @staticmethod
    def _validate_question(question: object) -> dict[str, object]:
        if not isinstance(question, dict):
            raise ValueError("Each benchmark question must be an object.")
        identifier = question.get("id")
        text = question.get("question")
        if not isinstance(identifier, str) or not identifier.strip() or not isinstance(text, str) or not text.strip():
            raise ValueError("Each benchmark question requires non-blank 'id' and 'question'.")
        fields = ("relevant_chunk_ids", "relevant_documents", "expected_citations")
        if any(not isinstance(question.get(field, []), list) for field in fields):
            raise ValueError("Benchmark relevance and citation fields must be lists.")
        expected = question.get("expected_citations", [])
        if any(
            not isinstance(value, dict)
            or not isinstance(value.get("document_name"), str)
            or not isinstance(value.get("page_number"), int)
            for value in expected
        ):
            raise ValueError("Expected citations require document_name and integer page_number.")
        difficulty = question.get("difficulty")
        if difficulty is not None and difficulty not in _DIFFICULTIES:
            raise ValueError("Benchmark difficulty must be easy, medium, or hard.")
        for field in _OPTIONAL_METADATA:
            if field in question and not isinstance(question[field], str):
                raise ValueError(f"Benchmark '{field}' must be a string when supplied.")
        return {
            "id": identifier,
            "question": text,
            "relevant_chunk_ids": tuple(str(value) for value in question.get("relevant_chunk_ids", [])),
            "relevant_documents": tuple(str(value) for value in question.get("relevant_documents", [])),
            "expected_citations": tuple(
                (str(value["document_name"]), int(value["page_number"]), value.get("section"))
                for value in expected
            ),
            "difficulty": difficulty,
            "category": question.get("category"),
            "hazard": question.get("hazard"),
            "agency": question.get("agency"),
        }
