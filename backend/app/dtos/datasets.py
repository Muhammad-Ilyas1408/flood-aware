"""Immutable application DTOs for configured dataset services."""

from dataclasses import dataclass

from backend.app.data.models import DatasetMetadata, DatasetStatistics


@dataclass(frozen=True, slots=True)
class VillageDTO:
    """Represent one village record prepared for application consumers."""

    name: str
    district: str
    population: int | None


@dataclass(frozen=True, slots=True)
class VillageListDTO:
    """Represent ordered village records prepared by the village service."""

    villages: tuple[VillageDTO, ...]


@dataclass(frozen=True, slots=True)
class ShelterDTO:
    """Represent one shelter record prepared for application consumers."""

    name: str
    district: str
    capacity: int


@dataclass(frozen=True, slots=True)
class ShelterListDTO:
    """Represent ordered shelter records prepared by the shelter service."""

    shelters: tuple[ShelterDTO, ...]


@dataclass(frozen=True, slots=True)
class DatasetSummaryDTO:
    """Represent exact metadata and statistics for one configured dataset."""

    metadata: DatasetMetadata
    statistics: DatasetStatistics


@dataclass(frozen=True, slots=True)
class DatasetCatalogDTO:
    """Represent independent summaries for configured village and shelter datasets."""

    villages: DatasetSummaryDTO
    shelters: DatasetSummaryDTO
