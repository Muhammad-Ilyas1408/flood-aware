"""Domain failures for multi-turn conversation orchestration."""

from backend.app.core.validation_exceptions import ValidationException


class ConversationError(Exception):
    """Base exception for conversation-domain failures."""


class ConversationSessionNotFoundError(ConversationError):
    """Raised when a supplied conversation session id has no active session."""


class MissingLocationError(ValidationException):
    """Raised when a flood-risk request has no coordinates or village name.

    Scoped to the flood-agent path only: Policy Advisor answers from
    government knowledge alone and never requires a location.
    """
