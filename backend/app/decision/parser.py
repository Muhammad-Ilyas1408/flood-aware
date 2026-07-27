"""Strict parsing and grounding validation of structured LLM decision output."""

import json

from pydantic import ValidationError

from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.exceptions import (
    DecisionGroundingError,
    DecisionParsingError,
    LLMOutputValidationError,
)
from backend.app.decision.models import Decision
from backend.app.graph.state import EvidenceBundle


class DecisionParser:
    """Own JSON parsing, schema validation, and grounding validation."""

    def parse(self, response_text: str, evidence: EvidenceBundle) -> Decision:
        """Validate one non-empty JSON object as a grounded, frozen ``Decision``.

        Raises:
            DecisionParsingError: If the provider output is not a JSON object.
            LLMOutputValidationError: If JSON violates the decision schema.
            DecisionGroundingError: If citations reference evidence that does
                not exist in the supplied bundle, or grounding is required
                but absent.
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
            decision = Decision.model_validate(payload)
        except ValidationError as error:
            raise LLMOutputValidationError(
                "Decision provider output does not match the decision contract."
            ) from error

        self._validate_grounding(decision, evidence)
        return decision

    def _validate_grounding(
        self, decision: Decision, evidence: EvidenceBundle
    ) -> None:
        """Reject decisions that cite evidence absent from the bundle."""
        allowed = EvidenceReferenceIndex.build(evidence)

        cited: set[str] = set(decision.recommendation.citations)
        cited.update(decision.recommendation.supporting_evidence)
        for action in decision.recommendation.actions:
            cited.update(action.evidence_references)
        for reason in decision.reasons:
            cited.update(reason.evidence_references)

        unknown = cited - allowed
        if unknown:
            raise DecisionGroundingError(
                f"Decision cites evidence not present in the bundle: {sorted(unknown)}"
            )

        if allowed and not cited:
            raise DecisionGroundingError(
                "Decision provides no citations despite available evidence."
            )