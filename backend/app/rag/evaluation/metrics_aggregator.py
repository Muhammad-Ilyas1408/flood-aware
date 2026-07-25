"""Aggregate lightweight evaluation records into report-ready metrics and warnings."""


class MetricsAggregator:
    """Aggregate numeric metric dictionaries without production RAG dependencies."""

    def aggregate(self, records: tuple[dict[str, object], ...]) -> dict[str, object]:
        """Return averaged retrieval/citation metrics and actionable warnings."""

        return {
            "benchmark_count": len(records),
            "retrieval_metrics": self._average(records, "retrieval_metrics"),
            "citation_metrics": self._average(records, "citation_metrics"),
            "warnings": self._warnings(records),
        }

    @staticmethod
    def _average(records: tuple[dict[str, object], ...], name: str) -> dict[str, float]:
        values: dict[str, list[float]] = {}
        for record in records:
            metrics = record[name]
            assert isinstance(metrics, dict)
            for key, value in metrics.items():
                assert isinstance(value, float)
                values.setdefault(key, []).append(value)
        return {key: sum(items) / len(items) for key, items in values.items()}

    @staticmethod
    def _warnings(records: tuple[dict[str, object], ...]) -> tuple[str, ...]:
        warnings: list[str] = []
        if any(record["retrieval_metrics"]["hit_rate"] == 0.0 for record in records):
            warnings.append(
                "One or more benchmark questions did not retrieve expected evidence."
            )
        if any(
            record["citation_metrics"]["invalid_citation_rate"] > 0.0
            for record in records
        ):
            warnings.append("One or more answers contained invalid citations.")
        if any(
            record["citation_metrics"]["missing_citation_rate"] > 0.0
            for record in records
        ):
            warnings.append("One or more answers were missing citations.")
        if any(not record["expected_citations_present"] for record in records):
            warnings.append(
                "One or more answers were missing expected benchmark citations."
            )
        return tuple(warnings)
