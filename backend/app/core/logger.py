"""Logger creation utilities for Flood-Aware modules."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return the named logger configured by the application logging setup.

    Args:
        name: The fully qualified name of the requesting module.

    Returns:
        The named standard-library logger.
    """

    return logging.getLogger(name)
