"""Immutable spatial evidence assembled for Flood-Aware AI decision support."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from backend.app.forecast.models import ForecastResult
from backend.app.gis.processing.exceptions import FloodEvidenceError
from backend.app.gis.processing.models import (
    ElevationSample,
    FloodZone,
    InfrastructureImpactSummary,
    PopulationExposureResult,
)


@dataclass(frozen=True, slots=True)
class FloodEvidence:
    """Combine validated flood facts into one AI-ready, non-interpretive record.

    The embedded forecast retains its source metadata, including dataset identity,
    snapshot path, reference time, and retrieval time. This model contains only
    measured or calculated facts; it does not classify risk or recommend actions.
    """

    forecast: ForecastResult
    flood_zone: FloodZone
    flood_area_square_meters: float
    population_exposure: PopulationExposureResult
    infrastructure_impact: InfrastructureImpactSummary
    timestamp: datetime
    dem_elevation: ElevationSample | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        """Validate evidence integrity without performing GIS or AI calculations."""

        if not isinstance(self.forecast, ForecastResult):
            raise FloodEvidenceError("Flood evidence requires a ForecastResult.")
        if not isinstance(self.flood_zone, FloodZone):
            raise FloodEvidenceError("Flood evidence requires a FloodZone.")
        if not isinstance(self.population_exposure, PopulationExposureResult):
            raise FloodEvidenceError(
                "Flood evidence requires PopulationExposureResult."
            )
        if not isinstance(self.infrastructure_impact, InfrastructureImpactSummary):
            raise FloodEvidenceError(
                "Flood evidence requires InfrastructureImpactSummary."
            )
        if (
            isinstance(self.flood_area_square_meters, bool)
            or not isinstance(self.flood_area_square_meters, (int, float))
            or not isfinite(float(self.flood_area_square_meters))
            or self.flood_area_square_meters <= 0
        ):
            raise FloodEvidenceError(
                "Flood evidence requires a positive finite flood area."
            )
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None:
            raise FloodEvidenceError("Flood evidence timestamp must be timezone-aware.")
        if self.dem_elevation is not None and not isinstance(
            self.dem_elevation, ElevationSample
        ):
            raise FloodEvidenceError(
                "DEM elevation must be an ElevationSample or None."
            )
        if self.confidence is not None:
            if (
                isinstance(self.confidence, bool)
                or not isinstance(self.confidence, (int, float))
                or not isfinite(float(self.confidence))
                or not 0.0 <= self.confidence <= 1.0
            ):
                raise FloodEvidenceError(
                    "Evidence confidence must be between 0.0 and 1.0."
                )


class FloodEvidenceBuilder:
    """Assemble existing forecast and GIS outputs without recalculating evidence."""

    def build(
        self,
        forecast: ForecastResult,
        flood_zone: FloodZone,
        population_exposure: PopulationExposureResult,
        infrastructure_impact: InfrastructureImpactSummary,
        dem_elevation: ElevationSample | None = None,
        confidence: float | None = None,
    ) -> FloodEvidence:
        """Return immutable evidence from already-computed spatial facts.

        Args:
            forecast: Canonical local hydrological forecast and its provenance.
            flood_zone: Deterministic severity-buffer flood geometry.
            population_exposure: Existing WorldPop exposure calculation.
            infrastructure_impact: Existing affected-asset count summary.
            dem_elevation: Optional elevation sampled by ``DEMLoader``.
            confidence: Optional externally supplied factual confidence value.

        Returns:
            One immutable, AI-ready record. Its area and timestamp reuse existing
            upstream values rather than running duplicate calculations.

        Raises:
            FloodEvidenceError: If any supplied factual result is invalid.
        """

        if not isinstance(forecast, ForecastResult):
            raise FloodEvidenceError("Flood evidence requires a ForecastResult.")
        if not isinstance(population_exposure, PopulationExposureResult):
            raise FloodEvidenceError(
                "Flood evidence requires PopulationExposureResult."
            )
        return FloodEvidence(
            forecast=forecast,
            flood_zone=flood_zone,
            flood_area_square_meters=population_exposure.area_analyzed_square_meters,
            population_exposure=population_exposure,
            infrastructure_impact=infrastructure_impact,
            timestamp=forecast.metadata.retrieved_at,
            dem_elevation=dem_elevation,
            confidence=confidence,
        )
