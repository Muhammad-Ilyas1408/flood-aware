"""Immutable geometry models for the Flood-Aware GIS foundation."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.gis.crs import CRS
from backend.app.gis.exceptions import CRSError, GeometryError
from backend.app.gis.validation import validate_coordinate_pair, validate_crs


class Point(BaseModel):
    """Represent an immutable geographic point in a supported CRS."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latitude: float
    longitude: float
    crs: CRS = CRS.WGS84

    @field_validator("crs", mode="before")
    @classmethod
    def validate_point_crs(cls, value: CRS | int) -> CRS:
        """Validate the point coordinate reference system."""

        if not isinstance(value, (CRS, int)):
            raise CRSError("CRS must be a supported CRS or EPSG integer.")
        return validate_crs(value)

    @model_validator(mode="after")
    def validate_point_coordinates(self) -> "Point":
        """Validate the point coordinate pair using shared GIS validation."""

        validate_coordinate_pair(self.latitude, self.longitude)
        return self


class BoundingBox(BaseModel):
    """Represent an immutable latitude-longitude bounding box in WGS 84."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        """Validate coordinate ranges and ordering for this bounding box."""

        validate_coordinate_pair(self.min_latitude, self.min_longitude)
        validate_coordinate_pair(self.max_latitude, self.max_longitude)
        if (
            self.min_latitude > self.max_latitude
            or self.min_longitude > self.max_longitude
        ):
            raise GeometryError(
                "Bounding box minimum coordinates must not exceed maximum coordinates."
            )
        return self

    def contains(self, point: Point) -> bool:
        """Return whether a point lies within this bounding box, including its boundary."""

        return (
            self.min_latitude <= point.latitude <= self.max_latitude
            and self.min_longitude <= point.longitude <= self.max_longitude
        )

    def center(self) -> Point:
        """Return the arithmetic center point of this bounding box."""

        return Point(
            latitude=(self.min_latitude + self.max_latitude) / 2,
            longitude=(self.min_longitude + self.max_longitude) / 2,
        )

    def width(self) -> float:
        """Return the longitudinal span of this bounding box in decimal degrees."""

        return self.max_longitude - self.min_longitude

    def height(self) -> float:
        """Return the latitudinal span of this bounding box in decimal degrees."""

        return self.max_latitude - self.min_latitude


class DistanceResult(BaseModel):
    """Represent an immutable distance result without performing calculations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    meters: float = Field(ge=0)
    kilometers: float = Field(ge=0)
