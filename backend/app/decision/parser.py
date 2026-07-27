"""Strict parsing of structured LLM decision output."""

import json

from pydantic import ValidationError

from backend.app.decision.exceptions import (
    DecisionParsingError,
    LLMOutputValidationError,
)
from backend.app.decision.models import Decision


class DecisionParser:
    """Own JSON parsing and contract validation for provider output.

    The parser is provider-independent and performs no provider calls. It converts
    JSON-only output into the canonical immutable decision model or raises a
    domain-specific validation error.
    """

    def parse(self, response_text: str) -> Decision:
        """Validate one non-empty JSON object as a frozen ``Decision``.

        Raises:
            DecisionParsingError: If the provider output is not a JSON object.
            LLMOutputValidationError: If JSON violates the decision schema.
        """
        if not isinstance(response_text, str) or not response_text.strip():
            raise DecisionParsingError("Decision provider returned an empty response.")
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise DecisionParsingError(
                "Decision provider returned invalid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise DecisionParsingError("Decision provider must return a JSON object.")
        try:
            return Decision.model_validate(payload)
        except ValidationError as error:
            raise LLMOutputValidationError(
                "Decision provider output does not match the decision contract."
            ) from error
