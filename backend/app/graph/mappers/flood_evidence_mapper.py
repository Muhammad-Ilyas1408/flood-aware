"""Map canonical GIS domain evidence into immutable graph evidence."""

from backend.app.gis.evidence import FloodEvidence
from backend.app.graph.state import GISEvidence


class FloodEvidenceMapper:
    """Translate factual ``FloodEvidence`` fields into the graph-state contract."""

    @staticmethod
    def to_graph(evidence: FloodEvidence) -> GISEvidence:
        """Return immutable graph evidence without recalculating GIS facts."""
        return GISEvidence(
            flood_zone=evidence.flood_zone.severity.value,
            population_exposed=float(evidence.population_exposure.exposed_population),
            infrastructure_exposed=(
                evidence.infrastructure_impact.critical_assets_affected
            ),
            affected_area=evidence.flood_area_square_meters,
            confidence=evidence.confidence,
        )
