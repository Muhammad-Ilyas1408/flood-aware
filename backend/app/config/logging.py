"""Application logging configuration."""

import logging

from backend.app.config.settings import LogLevel

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_STANDARD_LOG_RECORD_FIELDS = frozenset(
    logging.LogRecord(
        name="",
        level=logging.NOTSET,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
)


class ExtraFieldsFormatter(logging.Formatter):
    """Render arbitrary structured logging fields after the formatted message."""

    def format(self, record: logging.LogRecord) -> str:
        """Append non-standard ``LogRecord`` attributes as stable key-value pairs."""
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_FIELDS
        }
        formatted = super().format(record)
        if not extras:
            return formatted
        fields = " ".join(f"{key}={value}" for key, value in sorted(extras.items()))
        return f"{formatted} {fields}"


def configure_logging(log_level: LogLevel) -> None:
    """Configure idempotent console logging for the application.

    Args:
        log_level: The logging level name loaded from application settings.

    Raises:
        ValueError: If ``log_level`` is not a supported logging level.
    """

    normalized_level = log_level.upper()
    numeric_level = logging.getLevelNamesMapping().get(normalized_level)
    if numeric_level is None:
        raise ValueError(f"Unsupported log level: {log_level}")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ExtraFieldsFormatter(LOG_FORMAT))
        root_logger.addHandler(console_handler)

    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)
