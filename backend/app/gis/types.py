"""Small shared type aliases for GIS processing contracts."""

from pathlib import Path
from typing import TypeAlias

import geopandas as gpd
import numpy.ma as ma
from shapely.geometry.base import BaseGeometry

CRSType: TypeAlias = str
GeometryType: TypeAlias = BaseGeometry
RasterPath: TypeAlias = Path
PopulationValue: TypeAlias = float
ElevationValue: TypeAlias = float
AreaSquareMeters: TypeAlias = float
RasterArray: TypeAlias = ma.MaskedArray
InfrastructureLayer: TypeAlias = gpd.GeoDataFrame
