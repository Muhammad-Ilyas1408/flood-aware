"""Immutable metadata contracts for future Flood-Aware data sources."""

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from backend.app.data.exceptions import DatasetMetadataError, DatasetValidationError
from backend.app.data.validation import (
    validate_dataset_bounds,
    validate_dataset_description,
    validate_dataset_name,
    validate_dataset_path,
    validate_dataset_source,
    validate_dataset_version,
)
from backend.app.gis.crs import CRS
from backend.app.gis.exceptions import CRSError
from backend.app.gis.geometry import BoundingBox
from backend.app.gis.validation import validate_crs


class DatasetBounds(BaseModel):
    """Describe the spatial extent of a dataset using the shared GIS bounding box."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bounding_box: BoundingBox

    @field_validator("bounding_box")
    @classmethod
    def validate_bounding_box(cls, value: BoundingBox) -> BoundingBox:
        """Validate the spatial bounds contract."""

        return validate_dataset_bounds(value)


class DatasetStatistics(BaseModel):
    """Describe aggregate dataset statistics without containing dataset records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_count: int

    @field_validator("record_count", mode="before")
    @classmethod
    def validate_record_count(cls, value: object) -> int:
        """Validate that the dataset record count is a nonnegative integer."""

        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DatasetValidationError(
                "Dataset record count must be a nonnegative integer."
            )
        return value


class DatasetMetadata(BaseModel):
    """Describe reusable metadata for a dataset independently of its storage format."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    version: str
    source: str
    created_at: AwareDatetime
    updated_at: AwareDatetime
    coordinate_system: CRS = CRS.WGS84
    spatial_bounds: DatasetBounds | None = None
    tags: tuple[str, ...] = ()

    @field_validator("name", "source", mode="before")
    @classmethod
    def validate_required_text(cls, value: object, info: ValidationInfo) -> str:
        """Validate required textual metadata fields."""

        if getattr(info, "field_name", None) == "name":
            return validate_dataset_name(value)
        return validate_dataset_source(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: object) -> str:
        """Validate the dataset description."""

        return validate_dataset_description(value)

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, value: object) -> str:
        """Validate the dataset version."""

        return validate_dataset_version(value)

    @field_validator("coordinate_system", mode="before")
    @classmethod
    def validate_coordinate_system(cls, value: CRS | int) -> CRS:
        """Validate the coordinate system through the shared GIS CRS contract."""

        try:
            return validate_crs(value)
        except CRSError as error:
            raise DatasetMetadataError("Dataset coordinate system is unsupported.") from error

    @field_validator("spatial_bounds")
    @classmethod
    def validate_spatial_bounds(cls, value: DatasetBounds | None) -> DatasetBounds | None:
        """Validate optional dataset spatial bounds."""

        if value is not None and not isinstance(value, DatasetBounds):
            raise DatasetValidationError("Dataset spatial bounds must be a DatasetBounds.")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: object) -> tuple[str, ...]:
        """Validate immutable textual dataset tags."""

        if not isinstance(value, (list, tuple)) or any(
            not isinstance(tag, str) for tag in value
        ):
            raise DatasetValidationError("Dataset tags must be a sequence of strings.")
        return tuple(value)

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "DatasetMetadata":
        """Ensure the metadata update timestamp does not precede its creation timestamp."""

        if self.updated_at < self.created_at:
            raise DatasetMetadataError(
                "Dataset updated timestamp must not precede created timestamp."
            )
        return self


class DatasetInfo(BaseModel):
    """Combine dataset metadata and statistics with an optional logical source path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: DatasetMetadata
    statistics: DatasetStatistics
    dataset_path: str | None = None

    @field_validator("dataset_path", mode="before")
    @classmethod
    def validate_path(cls, value: object) -> str | None:
        """Validate an optional path string without accessing the filesystem."""

        if value is None:
            return None
        return validate_dataset_path(value)
