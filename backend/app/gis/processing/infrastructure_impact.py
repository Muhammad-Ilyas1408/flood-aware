"""Flood-zone intersection analysis for OpenStreetMap infrastructure layers."""

from time import perf_counter

import geopandas as gpd
import pandas as pd

from backend.app.core.logger import get_logger
from backend.app.gis.processing.exceptions import InfrastructureImpactError
from backend.app.gis.processing.models import (
    FloodZone,
    InfrastructureImpact,
    InfrastructureImpactSummary,
    InfrastructureLayers,
)

_LOGGER = get_logger(__name__)


class InfrastructureImpactCalculator:
    """Calculate deterministic infrastructure intersections for one flood zone."""

    def calculate(
        self,
        flood_zone: FloodZone,
        layers: InfrastructureLayers,
    ) -> InfrastructureImpact:
        """Select infrastructure geometries that intersect a flood-zone polygon.

        Args:
            flood_zone: Flood polygon used as the analysis geometry.
            layers: OSM infrastructure layers to evaluate.

        Returns:
            Affected layers and immutable count summary.

        Raises:
            InfrastructureImpactError: If inputs or layer CRS values are invalid.
        """

        if not isinstance(flood_zone, FloodZone):
            raise InfrastructureImpactError(
                "Infrastructure impact requires a FloodZone."
            )
        if not isinstance(layers, InfrastructureLayers):
            raise InfrastructureImpactError(
                "Infrastructure impact requires InfrastructureLayers."
            )
        try:
            started_at = perf_counter()
            _LOGGER.debug(
                "Infrastructure impact calculation started: crs=%s", flood_zone.crs
            )
            roads = _intersecting(layers.roads, flood_zone)
            bridges = _intersecting(layers.bridges, flood_zone)
            schools = _intersecting(layers.schools, flood_zone)
            hospitals = _intersecting(layers.hospitals, flood_zone)
            clinics = _intersecting(layers.clinics, flood_zone)
            police_stations = _intersecting(layers.police_stations, flood_zone)
            fire_stations = _intersecting(layers.fire_stations, flood_zone)
            critical_assets = _critical_assets(
                hospitals,
                clinics,
                police_stations,
                fire_stations,
                flood_zone.crs,
            )
        except Exception as error:
            raise InfrastructureImpactError(
                "Infrastructure spatial intersection failed."
            ) from error

        summary = InfrastructureImpactSummary(
            roads_affected=len(roads),
            bridges_affected=len(bridges),
            schools_affected=len(schools),
            hospitals_affected=len(hospitals),
            clinics_affected=len(clinics),
            police_stations_affected=len(police_stations),
            fire_stations_affected=len(fire_stations),
            critical_assets_affected=len(critical_assets),
        )
        impact = InfrastructureImpact(
            roads=roads,
            bridges=bridges,
            schools=schools,
            hospitals=hospitals,
            clinics=clinics,
            police_stations=police_stations,
            fire_stations=fire_stations,
            critical_assets=critical_assets,
            summary=summary,
        )
        _LOGGER.info(
            "Infrastructure impact calculated: critical_assets=%s crs=%s duration_ms=%.2f",
            summary.critical_assets_affected,
            flood_zone.crs,
            (perf_counter() - started_at) * 1000,
        )
        return impact


def _intersecting(layer: gpd.GeoDataFrame, flood_zone: FloodZone) -> gpd.GeoDataFrame:
    """Project one layer and use its spatial index when available.

    Candidate positions are reordered to source order before the exact Shapely
    predicate runs, preserving the previous deterministic result ordering.
    """

    if not isinstance(layer, gpd.GeoDataFrame) or layer.crs is None:
        raise InfrastructureImpactError("Each infrastructure layer must have a CRS.")
    projected = (
        layer if str(layer.crs) == flood_zone.crs else layer.to_crs(flood_zone.crs)
    )
    if projected.empty:
        return projected.copy()
    try:
        candidate_positions = projected.sindex.query(
            flood_zone.geometry,
            predicate="intersects",
        )
        candidate_position_set = set(candidate_positions)
        candidates = projected.iloc[
            [
                position
                for position in range(len(projected))
                if position in candidate_position_set
            ]
        ]
        _LOGGER.debug(
            "Infrastructure spatial index used: candidates=%s features=%s",
            len(candidates),
            len(projected),
        )
    except (AttributeError, ImportError):
        candidates = projected
        _LOGGER.debug(
            "Infrastructure spatial index unavailable; using direct predicate."
        )
    return candidates.loc[candidates.geometry.intersects(flood_zone.geometry)].copy()


def _critical_assets(
    hospitals: gpd.GeoDataFrame,
    clinics: gpd.GeoDataFrame,
    police_stations: gpd.GeoDataFrame,
    fire_stations: gpd.GeoDataFrame,
    crs: str,
) -> gpd.GeoDataFrame:
    """Combine affected public-safety and health assets with category provenance."""

    categorized = []
    for asset_type, layer in (
        ("hospital", hospitals),
        ("clinic", clinics),
        ("police_station", police_stations),
        ("fire_station", fire_stations),
    ):
        if not layer.empty:
            categorized.append(layer.assign(asset_type=asset_type))
    if not categorized:
        return gpd.GeoDataFrame({"asset_type": []}, geometry=[], crs=crs)
    return gpd.GeoDataFrame(
        pd.concat(categorized, ignore_index=True),
        geometry="geometry",
        crs=crs,
    )
