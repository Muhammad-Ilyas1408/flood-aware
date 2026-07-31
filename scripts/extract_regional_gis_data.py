"""One-time extraction of Swat-region GIS data from the Pakistan-wide sources.

Standalone, manually-run maintenance script (not part of the request path,
matching ``scripts/ingest_glofas_snapshot.py``). It creates smaller, regional
companions to the existing Pakistan-wide OSM PBF and WorldPop raster so that
``RiverNetworkLoader.warm_up()`` / ``OSMLoader.warm_up()`` (see
``backend/app/config/graph_dependencies.py``) no longer have to parse the
entire country on every cold start when the application only ever analyzes
the Swat district region (``DEFAULT_SWAT_BOUNDING_BOX``).

The OSM extract is a full spatial extract (nodes/ways/relations, all tags
preserved, reference-complete) -- not a tag filter -- so every layer/column
currently read by ``RiverNetworkLoader`` and ``OSMLoader`` (waterways, roads,
bridges, and amenity-tagged points/multipolygons) survives unchanged. The
WorldPop raster is clipped to the same buffered extent with no other
modification.

This script only creates new files; it never modifies or deletes the
original Pakistan-wide sources.
"""

import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import osmium
import rasterio
from rasterio.mask import mask
from shapely.geometry import box

from backend.app.forecast.constants import DEFAULT_SWAT_BOUNDING_BOX
from backend.app.gis.geometry import BoundingBox

# The strict analysis extent is only 0.40 deg x 0.30 deg wide. A 0.2 deg
# margin (~20-22 km at this latitude) is added on every side so that no
# geometry a GIS query might touch near the strict boundary -- e.g. a river
# reach or road that starts just outside DEFAULT_SWAT_BOUNDING_BOX but
# intersects it once buffered for flood-zone analysis -- gets clipped away.
_BUFFER_DEGREES = 0.2

_SOURCE_OSM_PBF = PROJECT_ROOT / "data/gis/osm/raw/pakistan-latest.osm.pbf"
_TARGET_OSM_PBF = PROJECT_ROOT / "data/gis/osm/raw/swat-region.osm.pbf"
_SOURCE_WORLDPOP_TIF = PROJECT_ROOT / "data/gis/worldpop/raw/pak_ppp_2025.tif"
_TARGET_WORLDPOP_TIF = PROJECT_ROOT / "data/gis/worldpop/raw/swat-region_ppp_2025.tif"

_SEPARATOR = "=" * 41


def _buffered_bounding_box(bounds: BoundingBox, margin_degrees: float) -> BoundingBox:
    """Return ``bounds`` expanded by a fixed margin on every side."""

    return BoundingBox(
        min_latitude=bounds.min_latitude - margin_degrees,
        min_longitude=bounds.min_longitude - margin_degrees,
        max_latitude=bounds.max_latitude + margin_degrees,
        max_longitude=bounds.max_longitude + margin_degrees,
    )


class _SpatialExtractHandler:
    """Select OSM nodes/ways/relations intersecting a bounding box.

    Requires a ``FileProcessor`` with ``with_locations()`` enabled so that
    way nodes carry cached coordinates. Selection is a simple "any vertex/
    member falls in bounds" test -- deliberately permissive so it never
    drops a feature that a stricter geometric intersection test would keep,
    which is appropriate given the generous buffer already applied to the
    bounding box itself.
    """

    def __init__(self, writer: osmium.BackReferenceWriter, bounds: BoundingBox) -> None:
        self._writer = writer
        self._min_lon = bounds.min_longitude
        self._min_lat = bounds.min_latitude
        self._max_lon = bounds.max_longitude
        self._max_lat = bounds.max_latitude
        self._node_ids: set[int] = set()
        self._way_ids: set[int] = set()

    def _in_bounds(self, lon: float, lat: float) -> bool:
        return (
            self._min_lon <= lon <= self._max_lon
            and self._min_lat <= lat <= self._max_lat
        )

    def extract(self, source_path: Path) -> None:
        """Stream the source PBF once, writing every in-bounds feature."""

        file_processor = osmium.FileProcessor(source_path).with_locations()
        for obj in file_processor:
            if obj.is_node():
                self._handle_node(obj)
            elif obj.is_way():
                self._handle_way(obj)
            elif obj.is_relation():
                self._handle_relation(obj)

    def _handle_node(self, node) -> None:
        if not node.location.valid():
            return
        if self._in_bounds(node.location.lon, node.location.lat):
            self._writer.add_node(node)
            self._node_ids.add(node.id)

    def _handle_way(self, way) -> None:
        if not self._way_intersects(way):
            return
        self._writer.add_way(way)
        self._way_ids.add(way.id)

    def _way_intersects(self, way) -> bool:
        for node_ref in way.nodes:
            if node_ref.ref in self._node_ids:
                return True
            try:
                if self._in_bounds(node_ref.lon, node_ref.lat):
                    return True
            except osmium.InvalidLocationError:
                continue
        return False

    def _handle_relation(self, relation) -> None:
        for member in relation.members:
            if member.type == "w" and member.ref in self._way_ids:
                self._writer.add_relation(relation)
                return
            if member.type == "n" and member.ref in self._node_ids:
                self._writer.add_relation(relation)
                return


def _extract_osm_region(bounds: BoundingBox) -> tuple[int, int]:
    """Write a reference-complete spatial extract of ``_SOURCE_OSM_PBF``.

    Returns:
        Before/after file sizes in bytes.
    """

    if _TARGET_OSM_PBF.exists():
        _TARGET_OSM_PBF.unlink()
    before_size = _SOURCE_OSM_PBF.stat().st_size
    with osmium.BackReferenceWriter(
        _TARGET_OSM_PBF,
        ref_src=_SOURCE_OSM_PBF,
        remove_tags=False,
    ) as writer:
        _SpatialExtractHandler(writer, bounds).extract(_SOURCE_OSM_PBF)
    after_size = _TARGET_OSM_PBF.stat().st_size
    return before_size, after_size


def _clip_worldpop_region(bounds: BoundingBox) -> tuple[int, int]:
    """Clip ``_SOURCE_WORLDPOP_TIF`` to ``bounds`` and write the regional raster.

    Returns:
        Before/after file sizes in bytes.
    """

    before_size = _SOURCE_WORLDPOP_TIF.stat().st_size
    clip_geometry = box(
        bounds.min_longitude, bounds.min_latitude,
        bounds.max_longitude, bounds.max_latitude,
    )
    with rasterio.open(_SOURCE_WORLDPOP_TIF) as dataset:
        values, transform = mask(
            dataset, [clip_geometry], crop=True, filled=True,
            nodata=dataset.nodata,
        )
        profile = dataset.profile.copy()
        profile.update(
            height=values.shape[1],
            width=values.shape[2],
            transform=transform,
        )
        with rasterio.open(_TARGET_WORLDPOP_TIF, "w", **profile) as target:
            target.write(values)
    after_size = _TARGET_WORLDPOP_TIF.stat().st_size
    return before_size, after_size


def main() -> int:
    """Extract the buffered Swat-region OSM PBF and WorldPop raster.

    Returns:
        A process exit code indicating whether extraction succeeded.
    """

    for source_path in (_SOURCE_OSM_PBF, _SOURCE_WORLDPOP_TIF):
        if not source_path.is_file():
            print(f"Regional GIS extraction failed: missing source {source_path}")
            return 1

    bounds = _buffered_bounding_box(DEFAULT_SWAT_BOUNDING_BOX, _BUFFER_DEGREES)
    started_at = perf_counter()

    osm_before, osm_after = _extract_osm_region(bounds)
    worldpop_before, worldpop_after = _clip_worldpop_region(bounds)

    elapsed_seconds = perf_counter() - started_at
    _print_report(bounds, osm_before, osm_after, worldpop_before, worldpop_after, elapsed_seconds)
    return 0


def _print_report(
    bounds: BoundingBox,
    osm_before: int,
    osm_after: int,
    worldpop_before: int,
    worldpop_after: int,
    elapsed_seconds: float,
) -> None:
    """Print a concise manual-verification report."""

    print(_SEPARATOR)
    print("Flood-Aware Regional GIS Extraction (Swat)")
    print(_SEPARATOR)
    print()
    print(
        "Buffered bounding box: "
        f"min_lat={bounds.min_latitude}, min_lon={bounds.min_longitude}, "
        f"max_lat={bounds.max_latitude}, max_lon={bounds.max_longitude} "
        f"(margin={_BUFFER_DEGREES} deg)"
    )
    print()
    print(f"OSM source: {_SOURCE_OSM_PBF}")
    print(f"OSM output: {_TARGET_OSM_PBF}")
    print(f"OSM size before: {osm_before:,} bytes")
    print(f"OSM size after:  {osm_after:,} bytes")
    print()
    print(f"WorldPop source: {_SOURCE_WORLDPOP_TIF}")
    print(f"WorldPop output: {_TARGET_WORLDPOP_TIF}")
    print(f"WorldPop size before: {worldpop_before:,} bytes")
    print(f"WorldPop size after:  {worldpop_after:,} bytes")
    print()
    print(f"Elapsed time: {elapsed_seconds:.2f} seconds")
    print()
    print("Extraction Successful")


if __name__ == "__main__":
    raise SystemExit(main())
