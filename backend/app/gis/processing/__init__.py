"""Production GIS data-processing components for local flood analysis.

Public re-exports are resolved lazily to keep low-level cache and exception modules
independent from concrete processing implementations.
"""

from importlib import import_module
from typing import Any

__all__ = (
    "DEMLoader",
    "FloodZoneGenerator",
    "InfrastructureImpactCalculator",
    "OSMLoader",
    "PopulationExposureCalculator",
    "WorldPopLoader",
)

_PUBLIC_COMPONENTS = {
    "DEMLoader": ("backend.app.gis.processing.dem", "DEMLoader"),
    "FloodZoneGenerator": (
        "backend.app.gis.processing.flood_zone",
        "FloodZoneGenerator",
    ),
    "InfrastructureImpactCalculator": (
        "backend.app.gis.processing.infrastructure_impact",
        "InfrastructureImpactCalculator",
    ),
    "OSMLoader": ("backend.app.gis.processing.osm", "OSMLoader"),
    "PopulationExposureCalculator": (
        "backend.app.gis.processing.population_exposure",
        "PopulationExposureCalculator",
    ),
    "WorldPopLoader": ("backend.app.gis.processing.worldpop", "WorldPopLoader"),
}


def __getattr__(name: str) -> Any:
    """Lazily resolve supported public processing component re-exports."""

    try:
        module_name, attribute_name = _PUBLIC_COMPONENTS[name]
    except KeyError as error:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from error
    return getattr(import_module(module_name), attribute_name)
