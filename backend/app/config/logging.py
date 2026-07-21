"""Application logging configuration."""

import logging

from backend.app.config.settings import LogLevel


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


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
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(console_handler)

    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)
