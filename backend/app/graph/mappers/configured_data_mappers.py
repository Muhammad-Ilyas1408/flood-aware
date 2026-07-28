"""Map configured data-tool DTOs into immutable graph evidence."""

from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    ShelterListDTO,
    VillageListDTO,
)
from backend.app.graph.state import DatasetEvidence, ShelterEvidence, VillageEvidence


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
    """Translate configured shelter DTOs without ranking or filtering them."""

    @staticmethod
    def to_graph(result: ShelterListDTO) -> ShelterEvidence:
        """Return immutable shelter names while preserving configured order."""
        return ShelterEvidence(
            shelters=tuple(shelter.name for shelter in result.shelters)
        )


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
