"""Immutable configuration shared by Flood-Aware GIS processing components."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Mapping

from backend.app.models.enums import FloodSeverity


@dataclass(frozen=True, slots=True)
class CRSConfig:
    """Stable CRS values used for geographic and local metric processing."""

    default_crs: str = "EPSG:4326"
    northern_utm_epsg_base: int = 32600
    southern_utm_epsg_base: int = 32700
    utm_zone_width_degrees: float = 6.0
    longitude_offset_degrees: float = 180.0
    minimum_utm_zone: int = 1
    maximum_utm_zone: int = 60


@dataclass(frozen=True, slots=True)
class RasterConfig:
    """Stable raster cache, validation, and masking configuration."""

    minimum_dimension: int = 1
    cache_max_entries: int = 2
    mask_all_touched: bool = False


@dataclass(frozen=True, slots=True)
class InfrastructureConfig:
    """OpenStreetMap feature-selection configuration."""

    osm_pbf_suffixes: tuple[str, str] = (".osm", ".pbf")
    bridge_false_values: tuple[str, ...] = ("no", "false", "0")
    amenity_tags: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(
            {
                "schools": "school",
                "hospitals": "hospital",
                "clinics": "clinic",
                "police_stations": "police",
                "fire_stations": "fire_station",
            }
        )
    )


@dataclass(frozen=True, slots=True)
class PopulationConfig:
    """Stable units used by population exposure aggregation."""

    square_meters_per_square_kilometer: float = 1_000_000.0


FLOOD_BUFFER_METERS: Final[Mapping[FloodSeverity, float]] = MappingProxyType(
    {
        FloodSeverity.MINOR: 150.0,
        FloodSeverity.MODERATE: 300.0,
        FloodSeverity.MAJOR: 600.0,
        FloodSeverity.EXTREME: 1200.0,
    }
)


@dataclass(frozen=True, slots=True)
class GISProcessingConfiguration:
    """Compose the immutable GIS processing configuration groups.

    The compatibility properties retain the previously published flattened values,
    while new code can depend on the focused configuration groups.
    """

    crs: CRSConfig = CRSConfig()
    raster: RasterConfig = RasterConfig()
    infrastructure: InfrastructureConfig = InfrastructureConfig()
    population: PopulationConfig = PopulationConfig()

    @property
    def default_crs(self) -> str:
        """Return the compatibility alias for the default geographic CRS."""

        return self.crs.default_crs

    @property
    def northern_utm_epsg_base(self) -> int:
        """Return the northern UTM EPSG base."""

        return self.crs.northern_utm_epsg_base

    @property
    def southern_utm_epsg_base(self) -> int:
        """Return the southern UTM EPSG base."""

        return self.crs.southern_utm_epsg_base

    @property
    def utm_zone_width_degrees(self) -> float:
        """Return the UTM-zone longitudinal width."""

        return self.crs.utm_zone_width_degrees

    @property
    def longitude_offset_degrees(self) -> float:
        """Return the UTM-zone longitude offset."""

        return self.crs.longitude_offset_degrees

    @property
    def minimum_utm_zone(self) -> int:
        """Return the minimum supported UTM zone."""

        return self.crs.minimum_utm_zone

    @property
    def maximum_utm_zone(self) -> int:
        """Return the maximum supported UTM zone."""

        return self.crs.maximum_utm_zone

    @property
    def minimum_raster_dimension(self) -> int:
        """Return the compatibility alias for minimum raster dimension."""

        return self.raster.minimum_dimension

    @property
    def raster_cache_max_entries(self) -> int:
        """Return the compatibility alias for cache capacity."""

        return self.raster.cache_max_entries

    @property
    def raster_mask_all_touched(self) -> bool:
        """Return the compatibility alias for raster mask behavior."""

        return self.raster.mask_all_touched

    @property
    def square_meters_per_square_kilometer(self) -> float:
        """Return the compatibility alias for population area conversion."""

        return self.population.square_meters_per_square_kilometer

    @property
    def osm_pbf_suffixes(self) -> tuple[str, str]:
        """Return the compatibility alias for OSM PBF suffixes."""

        return self.infrastructure.osm_pbf_suffixes

    @property
    def bridge_false_values(self) -> tuple[str, ...]:
        """Return the compatibility alias for false-like bridge values."""

        return self.infrastructure.bridge_false_values


GIS_CONFIG: Final = GISProcessingConfiguration()
OSM_AMENITY_TAGS: Final[Mapping[str, str]] = GIS_CONFIG.infrastructure.amenity_tags
