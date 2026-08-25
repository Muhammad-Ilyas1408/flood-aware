"""Application data-transfer contracts for lightweight village condition summaries."""

from dataclasses import dataclass

from backend.app.village_summary.models import VillageConditionSummary


@dataclass(frozen=True, slots=True)
class VillageSummaryResultDTO:
    """Represent summaries for recognized villages and any unrecognized names.

    ``unknown_village_names`` preserves the honesty principle used elsewhere
    in this application: a requested village that is not in the configured
    dataset is reported explicitly rather than silently dropped.
    """

    summaries: tuple[VillageConditionSummary, ...]
    unknown_village_names: tuple[str, ...]
