"""Pure serializers between dataset contracts, CSV text, and GeoJSON models."""

import csv
from collections.abc import Mapping, Sequence
from datetime import datetime
from io import StringIO

from backend.app.data.exceptions import DatasetFormatError, DatasetValidationError
from backend.app.data.models import (
    DatasetColumnType,
    DatasetRow,
    DatasetSchema,
    DatasetTable,
)
from backend.app.gis.geojson import Feature, FeatureCollection, GeoJSONPoint


def dataset_table_to_csv(table: DatasetTable) -> str:
    """Serialize a dataset table to CSV text using its declared schema.

    Args:
        table: The validated dataset table to serialize.

    Returns:
        CSV text with schema columns and row values in their declared order.

    Raises:
        DatasetValidationError: If the input is not a dataset table or contains an
            unrepresentable nullable string value.
    """

    if not isinstance(table, DatasetTable):
        raise DatasetValidationError("CSV serialization requires a DatasetTable model.")

    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(column.name for column in table.dataset_schema.columns)

    for row in table.rows:
        serialized_row: list[str | int | float] = []
        for column, value in zip(table.dataset_schema.columns, row.values, strict=True):
            if value is None:
                if column.data_type is DatasetColumnType.STRING:
                    raise DatasetValidationError(
                        "CSV cannot represent null values in string columns."
                    )
                serialized_row.append("")
            elif isinstance(value, datetime):
                serialized_row.append(value.isoformat())
            elif isinstance(value, bool):
                serialized_row.append("true" if value else "false")
            else:
                serialized_row.append(value)
        writer.writerow(serialized_row)

    return output.getvalue()


def csv_to_dataset_table(csv_text: str, schema: DatasetSchema) -> DatasetTable:
    """Deserialize CSV text into a dataset table validated against an explicit schema.

    Args:
        csv_text: CSV text encoded with the scalar representation produced by this module.
        schema: The explicit schema that defines column order, types, and nullability.

    Returns:
        A validated dataset table containing the CSV rows in source order.

    Raises:
        DatasetFormatError: If the CSV text is malformed or contains an invalid scalar.
        DatasetValidationError: If the schema is invalid or CSV headers do not match it.
    """

    if not isinstance(csv_text, str):
        raise DatasetFormatError("CSV input must be text.")
    if not isinstance(schema, DatasetSchema):
        raise DatasetValidationError("CSV deserialization requires a DatasetSchema model.")

    expected_headers = tuple(column.name for column in schema.columns)
    rows: list[tuple[object, ...]] = []
    try:
        reader = csv.reader(StringIO(csv_text), strict=True)
        headers = next(reader, None)
        if headers is None:
            raise DatasetFormatError("CSV input must include a header row.")
        if tuple(headers) != expected_headers:
            raise DatasetValidationError("CSV headers must match the supplied schema.")

        for raw_row in reader:
            if len(raw_row) != len(schema.columns):
                raise DatasetValidationError(
                    "CSV row value count must match the supplied schema."
                )

            deserialized_row: list[object] = []
            for column, raw_value in zip(schema.columns, raw_row, strict=True):
                if column.data_type is DatasetColumnType.STRING:
                    deserialized_row.append(raw_value)
                elif raw_value == "":
                    deserialized_row.append(None)
                elif column.data_type is DatasetColumnType.INTEGER:
                    deserialized_row.append(int(raw_value))
                elif column.data_type is DatasetColumnType.FLOAT:
                    deserialized_row.append(float(raw_value))
                elif column.data_type is DatasetColumnType.BOOLEAN:
                    if raw_value not in {"true", "false"}:
                        raise ValueError
                    deserialized_row.append(raw_value == "true")
                else:
                    deserialized_row.append(datetime.fromisoformat(raw_value))
            rows.append(tuple(deserialized_row))
    except csv.Error as error:
        raise DatasetFormatError("CSV input is malformed.") from error
    except ValueError as error:
        raise DatasetFormatError("CSV value does not match the supplied schema.") from error

    return _build_dataset_table(schema, rows)


def row_mappings_to_dataset_table(
    rows: Sequence[Mapping[str, str]],
    schema: DatasetSchema,
) -> DatasetTable:
    """Deserialize parsed CSV row mappings into a validated dataset table.

    Args:
        rows: Parsed CSV rows keyed by the supplied schema's column names.
        schema: The explicit schema that defines column order, types, and nullability.

    Returns:
        A validated dataset table containing the supplied rows in source order.

    Raises:
        DatasetFormatError: If a row contains an invalid scalar representation.
        DatasetValidationError: If row fields do not match the supplied schema.
    """

    if not isinstance(schema, DatasetSchema):
        raise DatasetValidationError("CSV deserialization requires a DatasetSchema model.")

    expected_headers = tuple(column.name for column in schema.columns)
    deserialized_rows: list[tuple[object, ...]] = []
    try:
        for row in rows:
            if tuple(row) != expected_headers:
                raise DatasetValidationError(
                    "CSV row fields must match the supplied schema."
                )

            deserialized_row: list[object] = []
            for column in schema.columns:
                raw_value = row[column.name]
                if column.data_type is DatasetColumnType.STRING:
                    deserialized_row.append(raw_value)
                elif raw_value == "":
                    deserialized_row.append(None)
                elif column.data_type is DatasetColumnType.INTEGER:
                    deserialized_row.append(int(raw_value))
                elif column.data_type is DatasetColumnType.FLOAT:
                    deserialized_row.append(float(raw_value))
                elif column.data_type is DatasetColumnType.BOOLEAN:
                    if raw_value not in {"true", "false"}:
                        raise ValueError
                    deserialized_row.append(raw_value == "true")
                else:
                    deserialized_row.append(datetime.fromisoformat(raw_value))
            deserialized_rows.append(tuple(deserialized_row))
    except ValueError as error:
        raise DatasetFormatError("CSV value does not match the supplied schema.") from error

    return _build_dataset_table(schema, deserialized_rows)


def dataset_table_to_feature_collection(
    table: DatasetTable,
    points: Sequence[GeoJSONPoint],
) -> FeatureCollection:
    """Serialize a dataset table and supplied point geometry into a FeatureCollection.

    Args:
        table: The validated dataset table to serialize as Feature properties.
        points: Ordered Point geometries aligned one-to-one with the dataset rows.

    Returns:
        A validated Point-only GeoJSON FeatureCollection.

    Raises:
        DatasetValidationError: If inputs are invalid or point and row counts differ.
    """

    if not isinstance(table, DatasetTable):
        raise DatasetValidationError("GeoJSON serialization requires a DatasetTable model.")
    if len(points) != len(table.rows):
        raise DatasetValidationError("GeoJSON point count must match dataset row count.")
    if any(not isinstance(point, GeoJSONPoint) for point in points):
        raise DatasetValidationError("GeoJSON serialization requires GeoJSONPoint models.")

    features: list[Feature] = []
    for point, row in zip(points, table.rows, strict=True):
        properties: dict[str, object] = {}
        for column, value in zip(table.dataset_schema.columns, row.values, strict=True):
            properties[column.name] = (
                value.isoformat() if isinstance(value, datetime) else value
            )
        features.append(Feature(geometry=point, properties=properties))
    return FeatureCollection(features=features)


def feature_collection_to_dataset_table(
    collection: FeatureCollection,
    schema: DatasetSchema,
) -> DatasetTable:
    """Deserialize Feature properties into a dataset table using an explicit schema.

    Args:
        collection: The validated Point-only FeatureCollection to deserialize.
        schema: The explicit schema required for property order, types, and nullability.

    Returns:
        A validated dataset table containing Feature properties in Feature order.

    Raises:
        DatasetValidationError: If inputs or Feature properties do not match the schema.
    """

    if not isinstance(collection, FeatureCollection):
        raise DatasetValidationError(
            "GeoJSON deserialization requires a FeatureCollection model."
        )
    if not isinstance(schema, DatasetSchema):
        raise DatasetValidationError(
            "GeoJSON deserialization requires a DatasetSchema model."
        )

    expected_columns = {column.name for column in schema.columns}
    rows: list[tuple[object, ...]] = []
    for feature in collection.features:
        properties = feature.properties
        if set(properties) != expected_columns:
            raise DatasetValidationError(
                "GeoJSON feature properties must exactly match the supplied schema."
            )

        deserialized_row: list[object] = []
        for column in schema.columns:
            value = properties[column.name]
            if isinstance(value, (dict, list, tuple)):
                raise DatasetValidationError(
                    "GeoJSON feature properties must contain scalar values."
                )
            if column.data_type is DatasetColumnType.DATETIME and value is not None:
                if not isinstance(value, str):
                    raise DatasetValidationError(
                        "GeoJSON datetime properties must be ISO 8601 strings."
                    )
                try:
                    value = datetime.fromisoformat(value)
                except ValueError as error:
                    raise DatasetValidationError(
                        "GeoJSON datetime properties must be ISO 8601 strings."
                    ) from error
            deserialized_row.append(value)
        rows.append(tuple(deserialized_row))

    return _build_dataset_table(schema, rows)


def _build_dataset_table(
    schema: DatasetSchema,
    rows: Sequence[tuple[object, ...]],
) -> DatasetTable:
    """Construct a validated dataset table from already ordered scalar row values."""

    return DatasetTable(
        dataset_schema=schema,
        rows=tuple(DatasetRow(values=row) for row in rows),
    )
