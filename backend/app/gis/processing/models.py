"""Typed models shared by GIS data-processing components."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import geopandas as gpd
from shapely.geometry.base import BaseGeometry

from backend.app.gis.types import (
    AreaSquareMeters,
    CRSType,
    ElevationValue,
    GeometryType,
    InfrastructureLayer,
    PopulationValue,
    RasterPath,
)
from backend.app.models.enums import FloodSeverity


@dataclass(frozen=True, slots=True)
class RasterMetadata:
    """Validated metadata describing one local geospatial raster."""

    path: RasterPath
    crs: CRSType
    width: int
    height: int
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    nodata: float | None


@dataclass(frozen=True, slots=True)
class ElevationSample:
    """One elevation value sampled from a DEM in meters."""

    elevation_meters: ElevationValue


@dataclass(frozen=True, slots=True)
class FloodZone:
    """Deterministic flood geometry with explicit spatial provenance."""

    geometry: GeometryType
    crs: CRSType
    severity: FloodSeverity
    buffer_meters: float

    def __post_init__(self) -> None:
        """Validate the immutable zone envelope."""

        if not isinstance(self.geometry, BaseGeometry) or self.geometry.is_empty:
            raise ValueError(
                "Flood zone geometry must be a non-empty Shapely geometry."
            )
        if not isinstance(self.crs, str) or not self.crs.strip():
            raise ValueError("Flood zone CRS must be a non-empty string.")
        if not isfinite(self.buffer_meters) or self.buffer_meters <= 0:
            raise ValueError("Flood zone buffer distance must be positive and finite.")


@dataclass(frozen=True, slots=True)
class PopulationExposureResult:
    """Immutable population-exposure statistics for one flood zone."""

    exposed_population: PopulationValue
    area_analyzed_square_meters: AreaSquareMeters
    population_density_per_square_kilometer: PopulationValue
    intersecting_cell_count: int
    minimum_cell_population: float | None
    maximum_cell_population: float | None
    mean_cell_population: float | None


@dataclass(frozen=True, slots=True)
class InfrastructureLayers:
    """OpenStreetMap infrastructure layers selected for flood-impact analysis."""

    roads: InfrastructureLayer
    bridges: InfrastructureLayer
    schools: InfrastructureLayer
    hospitals: InfrastructureLayer
    clinics: InfrastructureLayer
    police_stations: InfrastructureLayer
    fire_stations: InfrastructureLayer


@dataclass(frozen=True, slots=True)
class InfrastructureImpactSummary:
    """Immutable counts of flood-affected infrastructure assets."""

    roads_affected: int
    bridges_affected: int
    schools_affected: int
    hospitals_affected: int
    clinics_affected: int
    police_stations_affected: int
    fire_stations_affected: int
    critical_assets_affected: int


@dataclass(frozen=True, slots=True)
class InfrastructureImpact:
    """Affected infrastructure layers and their aggregate summary."""

    roads: gpd.GeoDataFrame
    bridges: gpd.GeoDataFrame
    schools: gpd.GeoDataFrame
    hospitals: gpd.GeoDataFrame
    clinics: gpd.GeoDataFrame
    police_stations: gpd.GeoDataFrame
    fire_stations: gpd.GeoDataFrame
    critical_assets: gpd.GeoDataFrame
    summary: InfrastructureImpactSummary
