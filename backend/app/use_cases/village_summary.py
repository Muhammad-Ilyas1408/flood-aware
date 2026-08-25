"""Application use case for lightweight, honest village condition summaries."""

from backend.app.dtos.village_summary import VillageSummaryResultDTO
from backend.app.services.protocols import VillageServiceProtocol
from backend.app.village_summary.models import VillageConditionSummary
from backend.app.village_summary.service import VillageSummaryService


class ViewVillageSummariesUseCase:
    """Coordinate lightweight condition summaries for explicitly requested villages."""

    def __init__(
        self,
        village_service: VillageServiceProtocol,
        summary_service: VillageSummaryService,
    ) -> None:
        """Initialize the use case with its village lookup and summary boundaries.

        Args:
            village_service: Loads the configured village dataset for name lookup.
            summary_service: Computes real, honest condition summaries.
        """

        self._village_service = village_service
        self._summary_service = summary_service

    def execute(self, village_names: tuple[str, ...]) -> VillageSummaryResultDTO:
        """Return summaries for each requested village, preserving request order."""
        villages_by_name = {
            village.name: village
            for village in self._village_service.load_villages().villages
        }
        summaries: list[VillageConditionSummary] = []
        unknown_village_names: list[str] = []
        for requested_name in village_names:
            village = villages_by_name.get(requested_name)
            if village is None:
                unknown_village_names.append(requested_name)
                continue
            summaries.append(
                self._summary_service.summarize(
                    name=village.name,
                    district=village.district,
                    latitude=village.latitude,
                    longitude=village.longitude,
                )
            )
        return VillageSummaryResultDTO(
            summaries=tuple(summaries),
            unknown_village_names=tuple(unknown_village_names),
        )
