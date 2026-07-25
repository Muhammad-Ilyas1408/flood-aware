"""Stable GloFAS defaults shared by forecast infrastructure."""

from pathlib import Path

from backend.app.gis.geometry import BoundingBox


DEFAULT_DATASET_NAME = "cems-glofas-forecast"
DEFAULT_PRODUCT_TYPE = "control_forecast"
DEFAULT_PRODUCT_LABEL = "control"
DEFAULT_HYDROLOGICAL_MODEL = "lisflood"
DEFAULT_VARIABLE = "river_discharge_in_the_last_24_hours"
DEFAULT_SYSTEM_VERSION = "operational"
DEFAULT_DATA_FORMAT = "netcdf"
DEFAULT_DOWNLOAD_FORMAT = "unarchived"
DEFAULT_SNAPSHOT_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "glofas"
DEFAULT_SWAT_BOUNDING_BOX = BoundingBox(
    min_latitude=34.70,
    min_longitude=72.15,
    max_latitude=35.00,
    max_longitude=72.55,
)
