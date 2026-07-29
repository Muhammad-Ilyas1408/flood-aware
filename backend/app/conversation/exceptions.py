"""Domain failures for multi-turn conversation orchestration."""


class ConversationError(Exception):
    """Base exception for conversation-domain failures."""


class ConversationSessionNotFoundError(ConversationError):
    """Raised when a supplied conversation session id has no active session."""
