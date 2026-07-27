"""Production orchestration boundary for deterministic GIS flood analysis."""

import asyncio
from dataclasses import dataclass
from time import perf_counter

from shapely.geometry.base import BaseGeometry

from backend.app.core.logger import get_logger
from backend.app.forecast.models import ForecastResult
from backend.app.gis.evidence import FloodEvidence, FloodEvidenceBuilder
from backend.app.gis.exceptions import GISAnalysisError, GISException
from backend.app.gis.processing.flood_zone import FloodZoneGenerator
from backend.app.gis.processing.infrastructure_impact import (
    InfrastructureImpactCalculator,
)
from backend.app.gis.processing.models import InfrastructureLayers
from backend.app.gis.processing.population_exposure import PopulationExposureCalculator
from backend.app.models.enums import FloodSeverity

_LOGGER = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GISAnalysisRequest:
    """Collect validated inputs required by the existing GIS processing pipeline.

    The request deliberately contains factual inputs only. Flood severity is
    supplied by an upstream component and is not interpreted by this tool.
    """

    forecast: ForecastResult
    severity: FloodSeverity
    river_geometry: BaseGeometry
    river_crs: str
    infrastructure_layers: InfrastructureLayers

    def __post_init__(self) -> None:
        """Validate request collaborators without duplicating GIS algorithms."""
        if not isinstance(self.forecast, ForecastResult):
            raise GISAnalysisError("GIS analysis requires a ForecastResult.")
        if not isinstance(self.severity, FloodSeverity):
            raise GISAnalysisError("GIS analysis requires a FloodSeverity.")
        if not isinstance(self.river_geometry, BaseGeometry):
            raise GISAnalysisError("GIS analysis requires river geometry.")
        if not isinstance(self.river_crs, str) or not self.river_crs.strip():
            raise GISAnalysisError("GIS analysis requires a river CRS.")
        if not isinstance(self.infrastructure_layers, InfrastructureLayers):
            raise GISAnalysisError("GIS analysis requires infrastructure layers.")


class GISAnalysisTool:
    """Coordinate existing GIS components to return canonical flood evidence.

    This tool owns sequencing and error translation only. Flood-zone generation,
    population calculations, infrastructure intersections, and evidence assembly
    remain owned by their established processing components.
    """

    def __init__(
        self,
        flood_zone_generator: FloodZoneGenerator,
        population_exposure_calculator: PopulationExposureCalculator,
        infrastructure_impact_calculator: InfrastructureImpactCalculator,
        flood_evidence_builder: FloodEvidenceBuilder,
    ) -> None:
        """Initialize explicit processing dependencies for one GIS workflow."""
        self._flood_zone_generator = flood_zone_generator
        self._population_exposure_calculator = population_exposure_calculator
        self._infrastructure_impact_calculator = infrastructure_impact_calculator
        self._flood_evidence_builder = flood_evidence_builder

    async def execute(self, request: GISAnalysisRequest) -> FloodEvidence:
        """Run the synchronous GIS pipeline without blocking an async caller.

        Args:
            request: Immutable upstream forecast and authoritative spatial inputs.

        Returns:
            Canonical immutable spatial evidence.

        Raises:
            GISAnalysisError: If input validation or a processing component fails.
        """
        return await asyncio.to_thread(self._execute_sync, request)

    def _execute_sync(self, request: GISAnalysisRequest) -> FloodEvidence:
        """Coordinate established GIS operations in their required order."""
        if not isinstance(request, GISAnalysisRequest):
            raise GISAnalysisError("GIS analysis requires a GISAnalysisRequest.")
        started_at = perf_counter()
        _LOGGER.info("GIS analysis started: severity=%s", request.severity.value)
        try:
            flood_zone = self._flood_zone_generator.generate(
                request.severity,
                request.river_geometry,
                request.river_crs,
            )
            population_exposure = self._population_exposure_calculator.calculate(
                flood_zone
            )
            infrastructure_impact = self._infrastructure_impact_calculator.calculate(
                flood_zone,
                request.infrastructure_layers,
            )
            evidence = self._flood_evidence_builder.build(
                request.forecast,
                flood_zone,
                population_exposure,
                infrastructure_impact.summary,
            )
        except GISException as error:
            _LOGGER.error("GIS analysis failed: error_type=%s", type(error).__name__)
            raise GISAnalysisError("GIS analysis processing failed.") from error
        except Exception as error:
            _LOGGER.exception(
                "GIS analysis failed unexpectedly: error_type=%s", type(error).__name__
            )
            raise GISAnalysisError("GIS analysis failed unexpectedly.") from error
        _LOGGER.info(
            "GIS analysis finished: severity=%s duration_ms=%.2f",
            request.severity.value,
            (perf_counter() - started_at) * 1000,
        )
        return evidence
