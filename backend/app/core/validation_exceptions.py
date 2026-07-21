"""Domain-specific exceptions raised by shared validation utilities."""


class ValidationException(Exception):
    """Represent a validation failure with optional structured diagnostic context."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: object | None = None,
    ) -> None:
        """Initialize a validation failure.

        Args:
            message: A safe, human-readable description of the validation failure.
            field: The affected contract field, when known.
            value: The rejected value for internal diagnostics.
        """

        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value


class CoordinateValidationError(ValidationException):
    """Represent invalid latitude or longitude values with coordinate context."""


class IdentifierValidationError(ValidationException):
    """Represent an identifier that does not meet the shared contract format."""


class DateRangeValidationError(ValidationException):
    """Represent a date range whose end precedes its start."""
