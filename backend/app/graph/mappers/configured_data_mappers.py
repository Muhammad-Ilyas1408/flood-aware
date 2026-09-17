"""Map configured data-tool DTOs into immutable graph evidence."""

from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageListDTO,
)
from backend.app.gis.distance import distance_kilometers
from backend.app.gis.geometry import Point
from backend.app.graph.state import (
    Coordinate,
    DatasetEvidence,
    ShelterEvidence,
    VillageEvidence,
)

# A shelter counts as relevant to a request location within this radius.
# 5km is roughly a one-hour walk (~5km/h), the standard rural/humanitarian
# evacuation-planning heuristic for a facility that is realistically
# reachable on foot during an emergency. It also matches this dataset's own
# structure: sorting Swat's real shelters by distance from Mingora shows
# every same-tehsil shelter within 3.53km, then a gap to 6.17km before the
# next tehsil's shelters begin -- 5km sits cleanly inside that gap.
DEFAULT_SHELTER_MATCH_RADIUS_KM = 5.0

_OPERATIONAL_STATUS = "Operational"


class VillageEvidenceMapper:
    """Translate configured village DTOs into graph-owned village evidence."""

    @staticmethod
    def to_graph(result: VillageListDTO) -> tuple[VillageEvidence, ...]:
        """Return one immutable graph record for every configured village."""
        return tuple(
            VillageEvidence(
                village_name=village.name,
                population=village.population,
                district=village.district,
            )
            for village in result.villages
        )


class ShelterEvidenceMapper:
    """Translate configured shelter DTOs into location-relevant graph evidence."""

    @staticmethod
    def to_graph(
        result: ShelterListDTO,
        *,
        origin: Coordinate | None = None,
        radius_km: float = DEFAULT_SHELTER_MATCH_RADIUS_KM,
    ) -> ShelterEvidence:
        """Return operational shelters within range of the request location.

        Without a request location, every configured shelter is returned
        unfiltered (the pre-existing behavior) since relevance cannot be
        computed. With a location, only ``Operational`` shelters within
        ``radius_km`` are returned, nearest first, and the closest one is
        recorded as ``nearest_shelter`` with its real capacity.
        """
        if origin is None:
            return ShelterEvidence(
                shelters=tuple(shelter.name for shelter in result.shelters)
            )

        origin_point = Point(latitude=origin.latitude, longitude=origin.longitude)
        nearby = sorted(
            (
                (distance_kilometers(origin_point, _shelter_point(shelter)), shelter)
                for shelter in result.shelters
                if shelter.status == _OPERATIONAL_STATUS
            ),
            key=lambda pair: pair[0],
        )
        within_radius = [shelter for distance, shelter in nearby if distance <= radius_km]
        nearest = within_radius[0] if within_radius else None
        return ShelterEvidence(
            shelters=tuple(shelter.name for shelter in within_radius),
            nearest_shelter=nearest.name if nearest is not None else None,
            available_capacity=nearest.capacity if nearest is not None else None,
        )


def _shelter_point(shelter: ShelterDTO) -> Point:
    """Return the WGS84 point for one configured shelter's coordinates."""
    return Point(latitude=shelter.latitude, longitude=shelter.longitude)


class DatasetEvidenceMapper:
    """Translate configured catalog provenance into graph-owned evidence."""

    @staticmethod
    def to_graph(result: DatasetCatalogDTO) -> DatasetEvidence:
        """Return catalog names and explicit source provenance without analysis."""
        summaries = (result.villages, result.shelters)
        return DatasetEvidence(
            datasets=(result.villages.metadata.name, result.shelters.metadata.name),
            provenance=tuple(
                f"{summary.metadata.name}:v{summary.metadata.version} "
                f"(source: {summary.metadata.source})"
                for summary in summaries
            ),
        )
