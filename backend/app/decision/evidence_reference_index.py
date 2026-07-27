"""Build the closed vocabulary of citable references for one evidence bundle."""

from backend.app.graph.state import EvidenceBundle


class EvidenceReferenceIndex:
    """Compute the exact set of strings a Decision is allowed to cite.

    Grounding is evidence-type/tool/entity level, not per-field, because the
    canonical EvidenceBundle does not assign per-fact identifiers. A citation
    is valid only if it exactly matches something derivable from the bundle.
    """

    @staticmethod
    def build(evidence: EvidenceBundle) -> frozenset[str]:
        """Return every valid citation string for the given evidence bundle."""
        refs: set[str] = set()

        for entry in evidence.provenance:
            refs.add(entry.evidence_type)
            refs.add(entry.tool_name)
            refs.add(f"{entry.evidence_type}:{entry.tool_name}")
            if entry.source:
                refs.add(entry.source)

        refs.update(evidence.knowledge.citations)
        refs.update(evidence.knowledge.retrieved_chunks)
        refs.update(evidence.datasets.provenance)
        refs.update(evidence.datasets.datasets)

        for village in evidence.villages:
            if village.village_name:
                refs.add(village.village_name)

        refs.update(evidence.shelters.shelters)
        if evidence.shelters.nearest_shelter:
            refs.add(evidence.shelters.nearest_shelter)

        # Coarse-grained fallbacks: always allow citing the evidence
        # section itself even if no explicit provenance record exists yet.
        if evidence.weather != evidence.weather.__class__():
            refs.add("weather")
        if evidence.forecast != evidence.forecast.__class__():
            refs.add("forecast")
        if evidence.gis != evidence.gis.__class__():
            refs.add("gis")

        return frozenset(refs)

    @staticmethod
    def has_any_evidence(evidence: EvidenceBundle) -> bool:
        """Return whether the bundle contains anything citable at all."""
        return bool(EvidenceReferenceIndex.build(evidence))