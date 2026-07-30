"""Domain failures for structured LLM decision generation."""

from enum import Enum


class DecisionError(Exception):
    """Base exception for decision-agent failures."""


class DecisionParsingError(DecisionError):
    """Raised when a provider response is not valid structured JSON."""


class LLMOutputValidationError(DecisionParsingError):
    """Raised when structured JSON does not satisfy the decision contract."""


class DecisionGenerationError(DecisionError):
    """Raised when the LLM provider cannot generate a decision."""


class DecisionFailureKind(str, Enum):
    """Classify failures without exposing provider-specific exception details."""

    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RATE_LIMITED = "rate_limited"
    INVALID_RESPONSE = "invalid_response"
    INVALID_JSON = "invalid_json"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    UNKNOWN_FAILURE = "unknown_failure"


class DecisionProviderError(DecisionGenerationError):
    """Base class for translated provider failures with a stable classification."""

    failure_kind: DecisionFailureKind


class DecisionProviderTimeoutError(DecisionProviderError):
    """Raised when a provider request exceeds its configured timeout."""

    failure_kind = DecisionFailureKind.PROVIDER_TIMEOUT


class DecisionProviderUnavailableError(DecisionProviderError):
    """Raised when a transient provider outage prevents decision generation."""

    failure_kind = DecisionFailureKind.PROVIDER_UNAVAILABLE


class DecisionRateLimitedError(DecisionProviderError):
    """Raised when the provider rejects a request because of rate limiting."""

    failure_kind = DecisionFailureKind.RATE_LIMITED


class DecisionCircuitOpenError(DecisionProviderError):
    """Raised when the provider circuit is open during a recovery interval."""

    failure_kind = DecisionFailureKind.PROVIDER_UNAVAILABLE


class DecisionUnknownProviderError(DecisionProviderError):
    """Raised for non-transient provider failures without leaking SDK details."""

    failure_kind = DecisionFailureKind.UNKNOWN_FAILURE


class DecisionGroundingError(DecisionGenerationError, LLMOutputValidationError):
    """Raised when a decision's citations are not grounded in its evidence."""

    def __init__(
        self, message: str, *, invalid_references: tuple[str, ...] = ()
    ) -> None:
        """Retain the exact invalid citation strings alongside the error message."""
        super().__init__(message)
        self.invalid_references = invalid_references


class DecisionSpecificityError(DecisionGroundingError):
    """Raised when a Decision ignores available quantitative evidence."""


class DecisionActionGroundingError(DecisionGroundingError):
    """Raised when a recommended action is grounded only in an absent category."""

    def __init__(
        self,
        message: str,
        *,
        rejected_action: str = "",
        absent_category: str = "",
    ) -> None:
        """Retain the rejected action text and absent category for correction."""
        super().__init__(message)
        self.rejected_action = rejected_action
        self.absent_category = absent_category
