"""Deterministic tests for the isolated GIS flood data-processing layer."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

GIS_PROCESSING_DEPENDENCIES_AVAILABLE = False

try:
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import LineString
    from shapely.geometry import Point as ShapelyPoint
    from shapely.geometry import Polygon

    from backend.app.gis.cache import RasterCache
    from backend.app.gis.config import FLOOD_BUFFER_METERS, GIS_CONFIG
    from backend.app.gis.geometry import BoundingBox, Point
    from backend.app.gis.processing.dem import DEMLoader
    from backend.app.gis.processing.exceptions import DEMError, FloodZoneError, OSMError
    from backend.app.gis.processing.flood_zone import FloodZoneGenerator
    from backend.app.gis.processing.infrastructure_impact import (
        InfrastructureImpactCalculator,
    )
    from backend.app.gis.processing.models import FloodZone, InfrastructureLayers
    from backend.app.gis.processing.osm import OSMLoader
    from backend.app.gis.processing.population_exposure import (
        PopulationExposureCalculator,
    )
    from backend.app.gis.processing.worldpop import WorldPopLoader
    from backend.app.gis.raster.utilities import clip_to_geometry, extract_metadata
    from backend.app.gis.types import AreaSquareMeters, RasterPath
    from backend.app.models.enums import FloodSeverity
except ModuleNotFoundError:
    pass
else:
    GIS_PROCESSING_DEPENDENCIES_AVAILABLE = True


@unittest.skipIf(
    not GIS_PROCESSING_DEPENDENCIES_AVAILABLE,
    "GIS processing dependencies are not installed in this Python environment.",
)
class GISProcessingTests(unittest.TestCase):
    """Verify GIS processing with local raster and vector fixtures only."""

    def test_dem_loader_reads_metadata_and_elevation(self) -> None:
        """DEM metadata and point sampling use validated, local raster data."""

        with TemporaryDirectory() as temporary_directory:
            path = _write_raster(Path(temporary_directory) / "dem.tif")
            loader = DEMLoader(path)
            metadata = loader.metadata()
            elevation = loader.elevation_at(Point(latitude=34.95, longitude=72.05))
            loader.close()

        self.assertEqual(metadata.width, 2)
        self.assertEqual(metadata.crs, "EPSG:4326")
        self.assertEqual(elevation.elevation_meters, 10.0)

    def test_dem_loader_rejects_missing_file(self) -> None:
        """A missing DEM is translated to a domain-specific error."""

        with self.assertRaises(DEMError):
            DEMLoader(Path("missing-dem.tif")).metadata()

    def test_flood_zone_generator_uses_deterministic_severity_buffers(self) -> None:
        """Severity maps to the approved metric buffer without hydraulic modelling."""

        river = LineString(((72.20, 34.90), (72.30, 34.95)))
        zone = FloodZoneGenerator().generate(FloodSeverity.MAJOR, river, "EPSG:4326")

        self.assertEqual(zone.buffer_meters, 600.0)
        self.assertEqual(zone.severity, FloodSeverity.MAJOR)
        self.assertFalse(zone.geometry.is_empty)

    def test_flood_zone_generator_rejects_unsupported_river_geometry(self) -> None:
        """Point geometries cannot be silently treated as authoritative river features."""

        with self.assertRaises(FloodZoneError):
            FloodZoneGenerator().generate(
                FloodSeverity.MINOR,
                ShapelyPoint(72.2, 34.9),
                "EPSG:4326",
            )

    def test_raster_cache_reuses_open_dataset_and_closes_it(self) -> None:
        """The instance-owned cache returns one reader and releases its file handle."""

        with TemporaryDirectory() as temporary_directory:
            path = _write_raster(Path(temporary_directory) / "cached.tif")
            cache = RasterCache(max_entries=GIS_CONFIG.raster_cache_max_entries)
            first = cache.get_dem(path)
            second = cache.get_dem(path)
            self.assertIs(first, second)
            cache.close()
            self.assertTrue(first.closed)

    def test_configuration_and_type_aliases_are_available(self) -> None:
        """Central GIS configuration and aliases remain importable runtime contracts."""

        self.assertEqual(GIS_CONFIG.default_crs, "EPSG:4326")
        self.assertEqual(FLOOD_BUFFER_METERS[FloodSeverity.EXTREME], 1200.0)
        self.assertIs(RasterPath, Path)
        self.assertIs(AreaSquareMeters, float)
        self.assertEqual(GIS_CONFIG.crs.default_crs, "EPSG:4326")
        self.assertEqual(GIS_CONFIG.raster.cache_max_entries, 2)
        self.assertEqual(
            GIS_CONFIG.population.square_meters_per_square_kilometer, 1_000_000.0
        )

    def test_raster_utilities_extract_and_clip(self) -> None:
        """Shared raster utilities preserve exposure-analysis raster behavior."""

        with TemporaryDirectory() as temporary_directory:
            first_path = _write_raster(Path(temporary_directory) / "first.tif")
            with rasterio.open(first_path) as first:
                metadata = extract_metadata(first, first_path)
                clipped, _ = clip_to_geometry(
                    first,
                    Polygon(((72.0, 34.8), (72.2, 34.8), (72.2, 35.0), (72.0, 35.0))),
                )

        self.assertEqual(metadata.width, 2)
        self.assertEqual(clipped.count(), 4)

    def test_worldpop_mask_and_population_exposure_are_local_and_deterministic(
        self,
    ) -> None:
        """A flood zone reads only intersecting population cells and aggregates them."""

        with TemporaryDirectory() as temporary_directory:
            path = _write_raster(
                Path(temporary_directory) / "worldpop.tif",
                values=np.array(((5.0, 10.0), (15.0, 20.0)), dtype="float32"),
                nodata=-99999.0,
            )
            zone = _fixture_flood_zone()
            loader = WorldPopLoader(path)
            metadata = loader.metadata()
            result = PopulationExposureCalculator(loader).calculate(zone)
            loader.close()

        self.assertEqual(metadata.path, path)
        self.assertEqual(result.exposed_population, 50.0)
        self.assertEqual(result.intersecting_cell_count, 4)
        self.assertGreater(result.area_analyzed_square_meters, 0)
        self.assertGreater(result.population_density_per_square_kilometer, 0)

    def test_osm_loader_extracts_requested_infrastructure_categories(self) -> None:
        """OSM tags are mapped to infrastructure layers without network access."""

        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "sample.osm.pbf"
            source.touch()
            lines, points, polygons = _fixture_osm_layers()
            with patch(
                "backend.app.gis.processing.osm.gpd.read_file",
                side_effect=(lines, points, polygons),
            ):
                layers = OSMLoader(source).load(
                    BoundingBox(
                        min_latitude=34.0,
                        min_longitude=72.0,
                        max_latitude=35.0,
                        max_longitude=73.0,
                    )
                )

        self.assertEqual(len(layers.roads), 2)
        self.assertEqual(len(layers.bridges), 1)
        self.assertEqual(len(layers.schools), 1)
        self.assertEqual(len(layers.hospitals), 1)
        self.assertEqual(len(layers.clinics), 1)
        self.assertEqual(len(layers.police_stations), 1)
        self.assertEqual(len(layers.fire_stations), 1)

    def test_osm_loader_rejects_wrong_source_type(self) -> None:
        """Only persisted OpenStreetMap PBF sources are accepted."""

        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "sample.geojson"
            source.touch()
            with self.assertRaises(OSMError):
                OSMLoader(source).load()

    def test_infrastructure_impact_uses_spatial_intersection(self) -> None:
        """All affected categories and critical assets are returned with stable counts."""

        lines, points, polygons = _fixture_osm_layers()
        layers = InfrastructureLayers(
            roads=lines.iloc[:1].copy(),
            bridges=lines.iloc[1:].copy(),
            schools=points.iloc[:1].copy(),
            hospitals=points.iloc[1:2].copy(),
            clinics=polygons.iloc[:1].copy(),
            police_stations=polygons.iloc[1:2].copy(),
            fire_stations=polygons.iloc[2:3].copy(),
        )

        impact = InfrastructureImpactCalculator().calculate(
            _fixture_flood_zone(), layers
        )

        self.assertEqual(impact.summary.roads_affected, 1)
        self.assertEqual(impact.summary.bridges_affected, 1)
        self.assertEqual(impact.summary.critical_assets_affected, 4)

    def test_infrastructure_impact_uses_available_spatial_index(self) -> None:
        """Spatial-index candidate filtering preserves the deterministic impact output."""

        lines, points, polygons = _fixture_osm_layers()
        self.assertIsNotNone(lines.sindex)
        layers = InfrastructureLayers(
            roads=lines,
            bridges=lines.iloc[0:0].copy(),
            schools=points.iloc[0:0].copy(),
            hospitals=points.iloc[0:0].copy(),
            clinics=polygons.iloc[0:0].copy(),
            police_stations=polygons.iloc[0:0].copy(),
            fire_stations=polygons.iloc[0:0].copy(),
        )

        impact = InfrastructureImpactCalculator().calculate(
            _fixture_flood_zone(), layers
        )

        self.assertEqual(impact.summary.roads_affected, 2)


def _write_raster(
    path: Path,
    *,
    values: object | None = None,
    nodata: float | None = None,
) -> Path:
    """Create a compact WGS84 raster fixture with non-identity transform metadata."""

    raster_values = (
        values
        if values is not None
        else np.array(((10.0, 20.0), (30.0, 40.0)), dtype="float32")
    )
    with rasterio.open(
        path,
        mode="w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(72.0, 35.0, 0.1, 0.1),
        nodata=nodata,
    ) as dataset:
        dataset.write(raster_values, 1)
    return path


def _fixture_flood_zone() -> FloodZone:
    """Return a zone covering all cells in the compact local raster fixture."""

    return FloodZone(
        geometry=Polygon(((72.0, 34.8), (72.2, 34.8), (72.2, 35.0), (72.0, 35.0))),
        crs="EPSG:4326",
        severity=FloodSeverity.MINOR,
        buffer_meters=150.0,
    )


def _fixture_osm_layers() -> (
    tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]
):
    """Return local GeoDataFrame fixtures matching OSM line, point, and polygon layers."""

    lines = gpd.GeoDataFrame(
        {"highway": ("primary", "secondary"), "bridge": (None, "yes")},
        geometry=[
            LineString(((72.02, 34.90), (72.18, 34.90))),
            LineString(((72.02, 34.95), (72.18, 34.95))),
        ],
        crs="EPSG:4326",
    )
    points = gpd.GeoDataFrame(
        {"amenity": ("school", "hospital")},
        geometry=[ShapelyPoint(72.05, 34.90), ShapelyPoint(72.10, 34.90)],
        crs="EPSG:4326",
    )
    polygons = gpd.GeoDataFrame(
        {"amenity": ("clinic", "police", "fire_station")},
        geometry=[
            ShapelyPoint(72.12, 34.90).buffer(0.005),
            ShapelyPoint(72.14, 34.90).buffer(0.005),
            ShapelyPoint(72.16, 34.90).buffer(0.005),
        ],
        crs="EPSG:4326",
    )
    return lines, points, polygons
