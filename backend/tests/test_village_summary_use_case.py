"""Focused unit tests for ViewVillageSummariesUseCase."""

from backend.app.dtos.datasets import VillageDTO, VillageListDTO
from backend.app.models.enums import FloodSeverity
from backend.app.use_cases.village_summary import ViewVillageSummariesUseCase
from backend.app.village_summary.models import VillageConditionSummary


class _FakeVillageService:
    """Return a fixed configured village list without external I/O."""

    def __init__(self, villages: tuple[VillageDTO, ...]) -> None:
        self._villages = villages

    def load_villages(self) -> VillageListDTO:
        return VillageListDTO(villages=self._villages)


class _RecordingSummaryService:
    """Record every request and return a deterministic summary per village."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def summarize(
        self, *, name: str, district: str, latitude: float, longitude: float
    ) -> VillageConditionSummary:
        self.calls.append(
            {
                "name": name,
                "district": district,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        return VillageConditionSummary(
            name=name,
            district=district,
            latitude=latitude,
            longitude=longitude,
            weather=None,
            weather_unavailable_reason="stub",
            severity=FloodSeverity.MINOR,
            severity_unavailable_reason=None,
            forecast_stale=False,
            status_message="Monitor conditions",
        )


_VILLAGES = (
    VillageDTO(name="Bishbanr", district="Swat", population=7212, latitude=34.75, longitude=72.35),
    VillageDTO(name="Kas", district="Swat", population=3143, latitude=34.74, longitude=72.34),
)


def test_execute_returns_summaries_for_known_villages_in_request_order() -> None:
    """Known villages are summarized in the order they were requested."""
    summary_service = _RecordingSummaryService()
    use_case = ViewVillageSummariesUseCase(_FakeVillageService(_VILLAGES), summary_service)

    result = use_case.execute(("Kas", "Bishbanr"))

    assert [summary.name for summary in result.summaries] == ["Kas", "Bishbanr"]
    assert result.unknown_village_names == ()
    assert summary_service.calls == [
        {"name": "Kas", "district": "Swat", "latitude": 34.74, "longitude": 72.34},
        {
            "name": "Bishbanr",
            "district": "Swat",
            "latitude": 34.75,
            "longitude": 72.35,
        },
    ]


def test_execute_reports_unrecognized_village_names_without_failing() -> None:
    """A request naming an unknown village does not fail the whole batch."""
    summary_service = _RecordingSummaryService()
    use_case = ViewVillageSummariesUseCase(_FakeVillageService(_VILLAGES), summary_service)

    result = use_case.execute(("Bishbanr", "NotARealVillage"))

    assert [summary.name for summary in result.summaries] == ["Bishbanr"]
    assert result.unknown_village_names == ("NotARealVillage",)
    assert len(summary_service.calls) == 1


def test_execute_returns_only_unknown_names_when_nothing_matches() -> None:
    """A request naming only unknown villages returns no summaries, not an error."""
    summary_service = _RecordingSummaryService()
    use_case = ViewVillageSummariesUseCase(_FakeVillageService(_VILLAGES), summary_service)

    result = use_case.execute(("Nowhere",))

    assert result.summaries == ()
    assert result.unknown_village_names == ("Nowhere",)
    assert summary_service.calls == []
