"""Point-only GeoJSON models and serialization helpers."""

import json
from collections.abc import Mapping
from typing import Any, Final, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.app.gis.exceptions import GeoJSONError
from backend.app.gis.geometry import Point
from backend.app.gis.validation import validate_coordinate_pair

GeoJSONModelT = TypeVar("GeoJSONModelT", "GeoJSONPoint", "Feature", "FeatureCollection")
GEOJSON_POINT_TYPE: Final[str] = "Point"
GEOJSON_FEATURE_TYPE: Final[str] = "Feature"
GEOJSON_FEATURE_COLLECTION_TYPE: Final[str] = "FeatureCollection"


class GeoJSONPoint(BaseModel):
    """Represent an immutable WGS 84 GeoJSON Point geometry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = GEOJSON_POINT_TYPE
    coordinates: tuple[float, float]

    @model_validator(mode="before")
    @classmethod
    def validate_point_structure(cls, value: object) -> object:
        """Validate the GeoJSON Point object structure and coordinate order."""

        data = _require_geojson_object(
            value,
            GEOJSON_POINT_TYPE,
            {"type", "coordinates"},
        )
        coordinates = data.get("coordinates")
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
            raise GeoJSONError(
                "GeoJSON Point coordinates must contain longitude and latitude."
            )

        longitude, latitude = coordinates
        validate_coordinate_pair(latitude, longitude)
        return data


class Feature(BaseModel):
    """Represent an immutable Point-only GeoJSON Feature."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = GEOJSON_FEATURE_TYPE
    geometry: GeoJSONPoint
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def validate_feature_structure(cls, value: object) -> object:
        """Validate Feature structure, Point geometry support, and properties."""

        data = _require_geojson_object(
            value,
            GEOJSON_FEATURE_TYPE,
            {"type", "geometry", "properties"},
        )
        if "geometry" not in data:
            raise GeoJSONError("GeoJSON Feature requires a geometry.")
        _validate_point_geometry(data["geometry"])

        properties = data.get("properties", {})
        if not isinstance(properties, dict) or not all(
            isinstance(key, str) for key in properties
        ):
            raise GeoJSONError(
                "GeoJSON Feature properties must be an object with string keys."
            )
        _validate_json_serializable(properties)
        return data


class FeatureCollection(BaseModel):
    """Represent an immutable ordered GeoJSON FeatureCollection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = GEOJSON_FEATURE_COLLECTION_TYPE
    features: list[Feature] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_collection_structure(cls, value: object) -> object:
        """Validate FeatureCollection structure and the features array."""

        data = _require_geojson_object(
            value,
            GEOJSON_FEATURE_COLLECTION_TYPE,
            {"type", "features"},
        )
        if "features" not in data or not isinstance(data["features"], list):
            raise GeoJSONError("GeoJSON FeatureCollection requires a features array.")
        return data


def point_to_geojson(point: Point) -> GeoJSONPoint:
    """Convert a Point to GeoJSON using coordinates ordered as [longitude, latitude].

    Raises:
        GeoJSONError: If the input is not a Point model.
    """

    if not isinstance(point, Point):
        raise GeoJSONError("GeoJSON conversion requires a Point model.")
    return GeoJSONPoint(coordinates=(point.longitude, point.latitude))


def geojson_to_point(geometry: GeoJSONPoint | Mapping[str, Any]) -> Point:
    """Convert [longitude, latitude] Point GeoJSON coordinates to a Flood-Aware Point.

    Raises:
        GeoJSONError: If the GeoJSON geometry structure is invalid or unsupported.
    """

    geojson_point = _coerce_geojson_point(geometry)
    longitude, latitude = geojson_point.coordinates
    return Point(latitude=latitude, longitude=longitude)


def feature_to_dict(feature: Feature) -> dict[str, Any]:
    """Serialize a GeoJSON Feature to a JSON-compatible dictionary.

    Raises:
        GeoJSONError: If the input is not a Feature model.
    """

    if not isinstance(feature, Feature):
        raise GeoJSONError("Feature serialization requires a Feature model.")
    return feature.model_dump(mode="json")


def feature_to_json(feature: Feature, *, indent: int | None = None) -> str:
    """Serialize a GeoJSON Feature to JSON, optionally using indentation."""

    return json.dumps(feature_to_dict(feature), ensure_ascii=False, indent=indent)


def feature_collection_to_dict(collection: FeatureCollection) -> dict[str, Any]:
    """Serialize a GeoJSON FeatureCollection to a JSON-compatible dictionary.

    Raises:
        GeoJSONError: If the input is not a FeatureCollection model.
    """

    if not isinstance(collection, FeatureCollection):
        raise GeoJSONError(
            "FeatureCollection serialization requires a FeatureCollection model."
        )
    return collection.model_dump(mode="json")


def geojson_point_to_dict(geometry: GeoJSONPoint) -> dict[str, Any]:
    """Serialize a GeoJSON Point with [longitude, latitude] coordinates to a dictionary.

    Raises:
        GeoJSONError: If the input is not a GeoJSONPoint model.
    """

    if not isinstance(geometry, GeoJSONPoint):
        raise GeoJSONError("GeoJSON Point serialization requires a GeoJSONPoint model.")
    return geometry.model_dump(mode="json")


def geojson_point_from_dict(value: Mapping[str, Any]) -> GeoJSONPoint:
    """Deserialize a dictionary into a validated GeoJSON Point geometry.

    GeoJSON coordinates are expected in [longitude, latitude] order.

    Raises:
        GeoJSONError: If the dictionary does not represent a valid Point geometry.
    """

    return _deserialize_model(GeoJSONPoint, value, "GeoJSON Point geometry")


def feature_from_dict(value: Mapping[str, Any]) -> Feature:
    """Deserialize a dictionary into a validated Point-only GeoJSON Feature.

    Raises:
        GeoJSONError: If the dictionary does not represent a valid supported Feature.
    """

    return _deserialize_model(Feature, value, "GeoJSON Feature")


def feature_from_json(value: str) -> Feature:
    """Deserialize a JSON string into a validated Point-only GeoJSON Feature.

    Raises:
        GeoJSONError: If the JSON value is invalid or not a supported Feature object.
    """

    return feature_from_dict(_json_object_from_string(value, "GeoJSON Feature"))


def feature_collection_from_dict(value: Mapping[str, Any]) -> FeatureCollection:
    """Deserialize a dictionary into a validated Point-only FeatureCollection.

    Raises:
        GeoJSONError: If the dictionary does not represent a valid FeatureCollection.
    """

    return _deserialize_model(FeatureCollection, value, "GeoJSON FeatureCollection")


def feature_collection_from_json(value: str) -> FeatureCollection:
    """Deserialize a JSON string into a validated Point-only FeatureCollection.

    Raises:
        GeoJSONError: If the JSON value is invalid or not a FeatureCollection object.
    """

    return feature_collection_from_dict(
        _json_object_from_string(value, "GeoJSON FeatureCollection")
    )


def feature_collection_to_json(
    collection: FeatureCollection,
    *,
    indent: int | None = None,
) -> str:
    """Serialize a GeoJSON FeatureCollection to JSON, optionally using indentation."""

    return json.dumps(
        feature_collection_to_dict(collection), ensure_ascii=False, indent=indent
    )


def _require_geojson_object(
    value: object,
    expected_type: str,
    allowed_fields: set[str],
) -> Mapping[str, Any]:
    """Validate a GeoJSON object envelope before Pydantic field parsing."""

    data = _require_mapping(value, expected_type)
    unexpected_fields = set(data) - allowed_fields
    if unexpected_fields:
        raise GeoJSONError(f"GeoJSON {expected_type} contains unsupported fields.")
    provided_type = data.get("type", expected_type)
    if provided_type != expected_type:
        raise GeoJSONError(f"Expected GeoJSON type {expected_type}.")
    return data


def _require_mapping(value: object, object_name: str) -> Mapping[str, Any]:
    """Return a mapping or raise a GeoJSON structure error."""

    if not isinstance(value, Mapping):
        raise GeoJSONError(f"{object_name} must be an object.")
    return value


def _validate_point_geometry(value: object) -> None:
    """Ensure Feature geometry is a Point geometry before nested validation."""

    if isinstance(value, GeoJSONPoint):
        return
    data = _require_mapping(value, "GeoJSON Feature geometry")
    if data.get("type") != GEOJSON_POINT_TYPE:
        raise GeoJSONError("Only GeoJSON Point geometries are supported.")


def _validate_json_serializable(value: object) -> None:
    """Ensure properties can be represented in JSON without exposing encoder errors."""

    try:
        json.dumps(value)
    except (TypeError, ValueError) as error:
        raise GeoJSONError(
            "GeoJSON Feature properties must be JSON serializable."
        ) from error


def _coerce_geojson_point(geometry: GeoJSONPoint | Mapping[str, Any]) -> GeoJSONPoint:
    """Return a validated GeoJSONPoint from a model or mapping input."""

    if isinstance(geometry, GeoJSONPoint):
        return geometry
    return geojson_point_from_dict(geometry)


def _json_object_from_string(value: str, object_name: str) -> Mapping[str, Any]:
    """Deserialize a JSON string into a mapping with stable GeoJSON errors."""

    if not isinstance(value, str):
        raise GeoJSONError("GeoJSON input must be a JSON string.")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise GeoJSONError("Invalid GeoJSON JSON string.") from error
    return _require_mapping(payload, object_name)


def _deserialize_model(
    model_type: type[GeoJSONModelT],
    value: object,
    object_name: str,
) -> GeoJSONModelT:
    """Deserialize a mapping into a GeoJSON model with domain-specific errors."""

    _require_mapping(value, object_name)
    try:
        return model_type.model_validate(value)
    except ValidationError as error:
        raise GeoJSONError(f"Invalid {object_name}.") from error
