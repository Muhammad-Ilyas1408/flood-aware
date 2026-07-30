"""Tests for authoritative OSM river-network ownership."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from backend.app.gis.geometry import BoundingBox
from backend.app.gis.river.exceptions import RiverNetworkError
from backend.app.gis.river.loader import RiverNetworkLoader


def _dataset_path(directory: str) -> Path:
    """Create an empty PBF path used only with mocked GeoPandas reads."""
    path = Path(directory) / "rivers.osm.pbf"
    path.touch()
    return path


def _waterways() -> gpd.GeoDataFrame:
    """Build deterministic OSM-style line features for loader tests."""
    return gpd.GeoDataFrame(
        {"waterway": ("river", "stream", "")},
        geometry=[
            LineString(((72.0, 34.0), (72.1, 34.1))),
            LineString(((72.1, 34.1), (72.2, 34.2))),
            LineString(((73.0, 35.0), (73.1, 35.1))),
        ],
        crs="EPSG:4326",
    )


def test_loader_discovers_loads_and_caches_authoritative_waterways() -> None:
    """Repeated equal queries should avoid repeated PBF reads."""
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        with patch(
            "backend.app.gis.river.loader.gpd.read_file", return_value=_waterways()
        ) as read_file:
            first = loader.get_geometry()
            second = loader.get_geometry()

    assert first is second
    assert first.crs == "EPSG:4326"
    assert read_file.call_count == 1


def test_loader_uses_bounded_query_and_preserves_crs() -> None:
    """A spatial query filters the in-memory layer and preserves its CRS."""
    bounds = BoundingBox(
        min_latitude=34.0,
        min_longitude=72.0,
        max_latitude=35.0,
        max_longitude=73.0,
    )
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        with patch(
            "backend.app.gis.river.loader.gpd.read_file", return_value=_waterways()
        ) as read_file:
            result = loader.get_geometry(bounds)

    assert result.geometry.geom_type in {"LineString", "MultiLineString"}
    assert result.crs == "EPSG:4326"
    read_file.assert_called_once_with(loader._dataset_path, layer="lines")


def _two_region_waterways() -> gpd.GeoDataFrame:
    """Build two valid waterway features in clearly separated regions."""
    return gpd.GeoDataFrame(
        {"waterway": ("river", "river")},
        geometry=[
            LineString(((72.0, 34.0), (72.1, 34.1))),
            LineString(((90.0, 10.0), (90.1, 10.1))),
        ],
        crs="EPSG:4326",
    )


def test_loader_parses_disk_once_across_multiple_distinct_bboxes() -> None:
    """Every distinct bbox must be served from the one in-memory parse result."""
    near_bounds = BoundingBox(
        min_latitude=33.5, min_longitude=71.5, max_latitude=34.5, max_longitude=72.5
    )
    far_bounds = BoundingBox(
        min_latitude=9.5, min_longitude=89.5, max_latitude=10.5, max_longitude=90.5
    )
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        with patch(
            "backend.app.gis.river.loader.gpd.read_file",
            return_value=_two_region_waterways(),
        ) as read_file:
            near = loader.get_geometry(near_bounds)
            far = loader.get_geometry(far_bounds)
            unbounded = loader.get_geometry()

    assert read_file.call_count == 1
    assert near.geometry.bounds[0] == pytest.approx(72.0)
    assert far.geometry.bounds[0] == pytest.approx(90.0)
    assert unbounded.geometry.geom_type == "MultiLineString"


def test_warm_up_parses_the_dataset_once_before_any_request() -> None:
    """Eager warm-up should let every later request avoid a disk read entirely."""
    bounds = BoundingBox(
        min_latitude=33.5, min_longitude=71.5, max_latitude=34.5, max_longitude=72.5
    )
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        with patch(
            "backend.app.gis.river.loader.gpd.read_file", return_value=_waterways()
        ) as read_file:
            loader.warm_up()
            loader.get_geometry(bounds)
            loader.get_geometry()

    assert read_file.call_count == 1


def test_loader_rejects_missing_dataset() -> None:
    """Dataset discovery should fail before GeoPandas is invoked."""
    with pytest.raises(RiverNetworkError):
        RiverNetworkLoader(Path("missing.osm.pbf")).get_geometry()


def test_loader_rejects_missing_crs_and_waterway_column() -> None:
    """Invalid source structure must not yield unauthoritative geometry."""
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        missing_crs = _waterways().set_crs(None, allow_override=True)
        with patch(
            "backend.app.gis.river.loader.gpd.read_file", return_value=missing_crs
        ):
            with pytest.raises(RiverNetworkError):
                loader.get_geometry()
        loader.close()
        with patch(
            "backend.app.gis.river.loader.gpd.read_file",
            return_value=_waterways().drop(columns="waterway"),
        ):
            with pytest.raises(RiverNetworkError):
                loader.get_geometry()


def test_close_releases_cached_results_for_a_repeatable_lifecycle() -> None:
    """Closing a loader should require the next access to read the dataset again."""
    with TemporaryDirectory() as directory:
        loader = RiverNetworkLoader(_dataset_path(directory))
        with patch(
            "backend.app.gis.river.loader.gpd.read_file", return_value=_waterways()
        ) as read_file:
            loader.get_geometry()
            loader.close()
            loader.get_geometry()

    assert read_file.call_count == 2
