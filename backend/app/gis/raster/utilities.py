"""Focused Rasterio utilities for metadata, clipping, alignment, and windows."""

from math import isfinite

import numpy.ma as ma
from pyproj import CRS as PyprojCRS
from rasterio.io import DatasetReader
from rasterio.mask import mask
from rasterio.transform import Affine
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from backend.app.gis.config import GIS_CONFIG
from backend.app.gis.processing.models import RasterMetadata
from backend.app.gis.types import RasterArray, RasterPath


def extract_metadata(dataset: DatasetReader, path: RasterPath) -> RasterMetadata:
    """Validate an open raster and return immutable application metadata.

    Args:
        dataset: Open Rasterio dataset reader.
        path: Logical local source path for provenance.

    Returns:
        Validated immutable raster metadata.

    Raises:
        ValueError: If the raster dimensions, CRS, transform, resolution, or bounds
            are invalid.
    """

    minimum_dimension = GIS_CONFIG.raster.minimum_dimension
    if (
        dataset.width < minimum_dimension
        or dataset.height < minimum_dimension
        or dataset.count < minimum_dimension
    ):
        raise ValueError("Raster dimensions and band count must be positive.")
    if dataset.crs is None:
        raise ValueError("Raster CRS is required.")
    crs = PyprojCRS.from_user_input(dataset.crs)
    if dataset.transform.is_identity:
        raise ValueError("Raster transform must not be the identity transform.")
    resolution = tuple(float(value) for value in dataset.res)
    bounds = (
        float(dataset.bounds.left),
        float(dataset.bounds.bottom),
        float(dataset.bounds.right),
        float(dataset.bounds.top),
    )
    if not all(isfinite(value) and value > 0 for value in resolution):
        raise ValueError("Raster resolution must be finite and positive.")
    if (
        not all(isfinite(value) for value in bounds)
        or bounds[0] >= bounds[2]
        or bounds[1] >= bounds[3]
    ):
        raise ValueError("Raster bounds must be finite and ordered.")
    nodata = float(dataset.nodata) if dataset.nodata is not None else None
    return RasterMetadata(
        path=path,
        crs=crs.to_string(),
        width=dataset.width,
        height=dataset.height,
        bounds=bounds,
        resolution=resolution,
        nodata=nodata,
    )


def clip_to_geometry(
    dataset: DatasetReader, geometry: BaseGeometry
) -> tuple[RasterArray, Affine]:
    """Return a cropped masked raster read for one geometry in the dataset CRS.

    Args:
        dataset: Open Rasterio dataset reader.
        geometry: Valid Shapely geometry expressed in the dataset CRS.

    Returns:
        Masked raster values and the cropped raster transform.

    Raises:
        ValueError: If the geometry is invalid or does not overlap the raster.
    """

    if (
        not isinstance(geometry, BaseGeometry)
        or geometry.is_empty
        or not geometry.is_valid
    ):
        raise ValueError("Raster clipping requires a valid non-empty geometry.")
    values, transform = mask(
        dataset,
        [mapping(geometry)],
        crop=True,
        filled=False,
        all_touched=GIS_CONFIG.raster.mask_all_touched,
    )
    return ma.masked_invalid(values[0]), transform
