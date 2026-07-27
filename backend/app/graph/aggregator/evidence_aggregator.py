"""Collect graph-owned evidence into the canonical immutable bundle."""

from collections import defaultdict
from collections.abc import Iterable

from backend.app.graph.state import (
    DatasetEvidence,
    EvidenceBundle,
    EvidenceConflict,
    EvidenceDuplicate,
    EvidenceObservation,
    EvidenceProvenance,
    ForecastEvidence,
    GISEvidence,
    GraphState,
    KnowledgeEvidence,
    ShelterEvidence,
    VillageEvidence,
    WeatherEvidence,
)


class EvidenceAggregator:
    """Aggregate existing graph evidence without changing node-owned facts.

    The aggregator is intentionally stateless. It projects the evidence already
    owned by nodes into one immutable bundle, attaches available provenance,
    and reports duplicate references or conflicting flood-severity values.
    """

    async def aggregate(self, state: GraphState) -> GraphState:
        """Return a new state containing the canonical collected evidence bundle."""
        provenance = self._provenance(state)
        bundle = EvidenceBundle(
            weather=state.weather,
            forecast=state.forecast,
            gis=state.gis,
            villages=state.villages,
            shelters=state.shelters,
            knowledge=state.knowledge,
            datasets=state.datasets,
            provenance=provenance,
            duplicates=self._duplicates(state, provenance),
            conflicts=self._conflicts(state, provenance),
        )
        return state.model_copy(update={"evidence_bundle": bundle})

    @staticmethod
    def _provenance(state: GraphState) -> tuple[EvidenceProvenance, ...]:
        """Collect available source facts in stable graph-evidence order."""
        entries: list[EvidenceProvenance] = []
        if _has_weather(state.weather):
            entries.append(
                EvidenceProvenance(
                    evidence_type="weather",
                    tool_name="WeatherTool",
                    source=state.weather.source,
                    observed_at=state.weather.observation_time,
                    confidence=state.weather.confidence,
                )
            )
        if _has_forecast(state.forecast) or state.forecast_result is not None:
            entries.append(
                EvidenceProvenance(
                    evidence_type="forecast",
                    tool_name="GloFASForecastTool",
                    source=(
                        state.forecast.source
                        if state.forecast.source is not None
                        else (
                            state.forecast_result.metadata.dataset_name
                            if state.forecast_result is not None
                            else None
                        )
                    ),
                    observed_at=(
                        state.forecast.forecast_date
                        if state.forecast.forecast_date is not None
                        else (
                            state.forecast_result.metadata.retrieved_at
                            if state.forecast_result is not None
                            else None
                        )
                    ),
                    confidence=state.forecast.confidence,
                )
            )
        if _has_gis(state.gis):
            entries.append(
                EvidenceProvenance(
                    evidence_type="gis",
                    tool_name="GISDomainService",
                    confidence=state.gis.confidence,
                    metadata=state.gis.processing_metadata,
                )
            )
        if state.villages:
            entries.append(
                EvidenceProvenance(
                    evidence_type="village",
                    tool_name="VillageTool",
                    confidence=_shared_confidence(state.villages),
                )
            )
        if _has_shelters(state.shelters):
            entries.append(
                EvidenceProvenance(
                    evidence_type="shelter",
                    tool_name="ShelterTool",
                    confidence=state.shelters.confidence,
                )
            )
        if _has_knowledge(state.knowledge):
            entries.append(
                EvidenceProvenance(
                    evidence_type="knowledge",
                    tool_name="KnowledgeTool",
                    confidence=state.knowledge.confidence,
                    metadata=state.knowledge.citations,
                )
            )
        if _has_datasets(state.datasets):
            entries.append(
                EvidenceProvenance(
                    evidence_type="dataset",
                    tool_name="DatasetCatalogTool",
                    confidence=state.datasets.confidence,
                    metadata=state.datasets.provenance,
                )
            )
        return tuple(entries)

    @staticmethod
    def _duplicates(
        state: GraphState,
        provenance: tuple[EvidenceProvenance, ...],
    ) -> tuple[EvidenceDuplicate, ...]:
        """Detect repeated source references while retaining every provenance."""
        origins_by_type = {origin.evidence_type: origin for origin in provenance}
        references: dict[str, list[EvidenceProvenance]] = defaultdict(list)
        for reference in state.datasets.provenance:
            origin = origins_by_type.get("dataset")
            if reference and origin is not None:
                references[reference].append(origin)
        for citation in state.knowledge.citations:
            origin = origins_by_type.get("knowledge")
            if citation and origin is not None:
                references[citation].append(origin)
        return tuple(
            EvidenceDuplicate(reference=reference, origins=tuple(origins))
            for reference, origins in sorted(references.items())
            if len(origins) > 1
        )

    @staticmethod
    def _conflicts(
        state: GraphState,
        provenance: tuple[EvidenceProvenance, ...],
    ) -> tuple[EvidenceConflict, ...]:
        """Record differing forecast and GIS severity facts without resolving them."""
        forecast_severity = state.forecast.severity
        gis_severity = state.gis.flood_zone
        if (
            not forecast_severity
            or not gis_severity
            or forecast_severity == gis_severity
        ):
            return ()
        origins_by_type = {origin.evidence_type: origin for origin in provenance}
        forecast_origin = origins_by_type.get("forecast")
        gis_origin = origins_by_type.get("gis")
        if forecast_origin is None or gis_origin is None:
            return ()
        return (
            EvidenceConflict(
                subject="flood_severity",
                observations=(
                    EvidenceObservation(
                        evidence_type="forecast",
                        value=forecast_severity,
                        origin=forecast_origin,
                    ),
                    EvidenceObservation(
                        evidence_type="gis",
                        value=gis_severity,
                        origin=gis_origin,
                    ),
                ),
            ),
        )


def _has_weather(evidence: WeatherEvidence) -> bool:
    """Return whether weather evidence contains at least one observed fact."""
    return any(
        value is not None
        for value in (
            evidence.temperature,
            evidence.rainfall,
            evidence.humidity,
            evidence.wind_speed,
            evidence.weather_condition,
            evidence.source,
            evidence.observation_time,
            evidence.confidence,
        )
    )


def _has_forecast(evidence: ForecastEvidence) -> bool:
    """Return whether forecast evidence contains at least one factual field."""
    return any(
        value is not None
        for value in (
            evidence.forecast_date,
            evidence.discharge,
            evidence.return_period,
            evidence.severity,
            evidence.lead_time,
            evidence.source,
            evidence.confidence,
        )
    )


def _has_gis(evidence: GISEvidence) -> bool:
    """Return whether GIS evidence contains at least one spatial fact."""
    return any(
        value is not None
        for value in (
            evidence.flood_zone,
            evidence.population_exposed,
            evidence.infrastructure_exposed,
            evidence.affected_area,
            evidence.exposure_level,
            evidence.raster_reference,
            evidence.confidence,
        )
    ) or bool(evidence.processing_metadata)


def _has_shelters(evidence: ShelterEvidence) -> bool:
    """Return whether shelter evidence contains an available factual value."""
    return bool(evidence.shelters) or any(
        value is not None
        for value in (
            evidence.nearest_shelter,
            evidence.available_capacity,
            evidence.confidence,
        )
    )


def _has_knowledge(evidence: KnowledgeEvidence) -> bool:
    """Return whether grounded knowledge contains passages or citations."""
    return (
        bool(evidence.retrieved_chunks or evidence.citations)
        or evidence.confidence is not None
    )


def _has_datasets(evidence: DatasetEvidence) -> bool:
    """Return whether dataset evidence contains names or provenance."""
    return (
        bool(evidence.datasets or evidence.provenance)
        or evidence.confidence is not None
    )


def _shared_confidence(evidence: Iterable[VillageEvidence]) -> float | None:
    """Return a common village confidence only when all records agree."""
    values = {item.confidence for item in evidence}
    return values.pop() if len(values) == 1 else None
