"""Application-level exceptions for runtime composition failures."""


class ApplicationError(Exception):
    """Base exception for application-level contract failures."""


class ApplicationConfigurationError(ApplicationError):
    """Represent missing or invalid runtime application configuration."""
