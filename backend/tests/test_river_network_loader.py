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
    """A spatial query should pass the documented GeoPandas bbox ordering."""
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
    assert read_file.call_args.kwargs["bbox"] == (72.0, 34.0, 73.0, 35.0)


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
