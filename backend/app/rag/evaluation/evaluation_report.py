"""Simple JSON and Markdown reporting for Government Knowledge Engine validation."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class EvaluationReportWriter:
    """Write the latest lightweight evaluation report in two useful formats."""

    def write(
        self, summary: dict[str, object], output_directory: str | Path
    ) -> tuple[Path, Path]:
        """Write ``evaluation.json`` and ``evaluation.md`` and return both paths."""

        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": datetime.now(UTC).isoformat(), **summary}
        json_path = directory / "evaluation.json"
        markdown_path = directory / "evaluation.md"
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        markdown_path.write_text(self._markdown(payload), encoding="utf-8")
        _LOGGER.info(
            "Evaluation reports written: json=%s markdown=%s", json_path, markdown_path
        )
        return json_path, markdown_path

    @staticmethod
    def _markdown(payload: dict[str, object]) -> str:
        retrieval = payload["retrieval_metrics"]
        citations = payload["citation_metrics"]
        warnings = payload["warnings"]
        assert (
            isinstance(retrieval, dict)
            and isinstance(citations, dict)
            and isinstance(warnings, tuple)
        )
        metrics = {**retrieval, **citations}
        metric_lines = "\n".join(
            f"- **{name}**: {value:.4f}" for name, value in metrics.items()
        )
        warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
        return (
            "# Government Knowledge Engine Evaluation\n\n"
            f"- **Timestamp**: {payload['timestamp']}\n"
            f"- **Benchmark questions**: {payload['benchmark_count']}\n"
            f"- **Pass**: {payload['pass']}\n\n"
            f"## Metrics\n\n{metric_lines}\n\n## Warnings\n\n{warning_lines}\n"
        )
