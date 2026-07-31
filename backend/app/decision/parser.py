"""Strict parsing and grounding validation of structured LLM decision output."""

import json
import re

from pydantic import ValidationError

from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.exceptions import (
    DecisionActionGroundingError,
    DecisionGroundingError,
    DecisionParsingError,
    DecisionSpecificityError,
    LLMOutputValidationError,
)
from backend.app.decision.models import Decision
from backend.app.decision.prompt_builder import (
    _entirely_absent_evidence_categories,
    _flood_severity_figures,
)
from backend.app.graph.state import EvidenceBundle

_QUANTITATIVE_FIGURE_PATTERN = re.compile(r"\d{2,}")
_SPECIFIC_ACTION_CLAIM_PATTERN = re.compile(
    r"\b(stock\w*|prepar\w*|assess\w*|activat\w*|ready|readiness|capacity)\b",
    re.IGNORECASE,
)

# _flood_severity_figures keys are "{prefix}.{field}"; most prefixes already
# match the category names _category_related_references matches against,
# except the plural "shelters" field prefix vs. the singular "shelter" name.
_FIGURE_PREFIX_TO_CATEGORY_NAME = {"shelters": "shelter"}


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
            DecisionActionGroundingError: If a recommended action is grounded
                only in an entirely-absent evidence category.
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
        self._validate_specificity(decision, evidence)
        self._validate_no_actions_on_absent_categories(decision, evidence)
        return decision

    def _validate_grounding(
        self, decision: Decision, evidence: EvidenceBundle
    ) -> None:
        """Reject decisions that cite evidence absent from the bundle."""
        allowed = EvidenceReferenceIndex.build(evidence)
        cited = _cited_references(decision)

        unknown = cited - allowed
        if unknown:
            raise DecisionGroundingError(
                f"Decision cites evidence not present in the bundle: {sorted(unknown)}",
                invalid_references=tuple(sorted(unknown)),
            )

        if allowed and not cited:
            raise DecisionGroundingError(
                "Decision provides no citations despite available evidence."
            )

    def _validate_specificity(
        self, decision: Decision, evidence: EvidenceBundle
    ) -> None:
        """Reject decisions that ignore available quantitative evidence.

        Exempts a figure-free response when the gap is honest, not evasive:
        every figure-bearing category the response left unquantified was
        never engaged (no citation, supporting_evidence, or evidence_reference
        touches it anywhere in the decision) — regardless of whether that
        category is entirely absent from the bundle or merely present but
        off-topic for this turn (e.g. a policy follow-up that never touches
        GIS/weather, per the FOCUS instruction). A category that IS
        cited/referenced but still left unquantified still raises: that is
        genuine evidence-ignoring, not an honest scope narrowing.
        """
        figures = _flood_severity_figures(evidence)
        if not figures:
            return

        text = " ".join(
            (
                decision.risk_assessment.rationale,
                decision.recommendation.summary,
                *(reason.statement for reason in decision.reasons),
            )
        )
        if _QUANTITATIVE_FIGURE_PATTERN.search(text):
            return

        if _unquantified_figures_are_uncited(decision, evidence, figures):
            return

        raise DecisionSpecificityError(
            "Decision ignores available quantitative evidence: "
            f"{sorted(figures)}"
        )

    def _validate_no_actions_on_absent_categories(
        self, decision: Decision, evidence: EvidenceBundle
    ) -> None:
        """Reject a specific-content action grounded only in an absent category.

        A valid (non-fabricated) reference can still name an absent category in
        passing, e.g. a dataset-catalog citation that happens to mention
        "shelters". Citation shape alone cannot distinguish a general
        data-gathering action (always acceptable, e.g. "obtain shelter data")
        from a specific-sounding claim about the resource itself (e.g. "assess
        and prepare existing shelters, ensuring they are stocked"): only the
        second is the real inconsistency this rejects. So this only fires when
        BOTH the action's evidence_references are entirely confined to one
        absent category's references AND its text contains direct-action
        claim language (stock/prepare/assess/activate/ready/capacity) rather
        than plain acquisition language (obtain/gather/collect/...), which is
        always allowed regardless of its references.
        """
        absent_categories = _entirely_absent_evidence_categories(evidence)
        if not absent_categories:
            return

        for action in decision.recommendation.actions:
            references = set(action.evidence_references)
            if not references:
                continue
            if not _SPECIFIC_ACTION_CLAIM_PATTERN.search(action.action):
                continue
            for category in absent_categories:
                category_references = _category_related_references(
                    evidence, category
                )
                if references <= category_references:
                    raise DecisionActionGroundingError(
                        "Decision recommends a specific action grounded only "
                        f"in the entirely-absent '{category}' category: "
                        f"{action.action!r}",
                        rejected_action=action.action,
                        absent_category=category,
                    )


def _cited_references(decision: Decision) -> set[str]:
    """Collect every citation-like reference the decision actually used."""
    cited: set[str] = set(decision.recommendation.citations)
    cited.update(decision.recommendation.supporting_evidence)
    for action in decision.recommendation.actions:
        cited.update(action.evidence_references)
    for reason in decision.reasons:
        cited.update(reason.evidence_references)
    return cited


def _unquantified_figures_are_uncited(
    decision: Decision, evidence: EvidenceBundle, figures: dict[str, str]
) -> bool:
    """Return whether every figure-bearing category was never engaged.

    "Engaged" means cited, supported, or referenced anywhere in the decision
    (citations, supporting_evidence, or any evidence_references). This is
    the sole gate, deliberately independent of whether a category is
    entirely absent or just present-but-unused for this turn: either way,
    a response that never touched a category's evidence at all cannot be
    accused of silently dropping a number from it. If even one figure-
    bearing category WAS engaged but its number still never appears in the
    text, this returns False and the specificity check still fires — that
    is genuine evidence-ignoring, not honest scope narrowing.
    """
    cited = _cited_references(decision)
    figure_prefixes = {key.split(".", 1)[0] for key in figures}
    figure_categories = {
        _FIGURE_PREFIX_TO_CATEGORY_NAME.get(prefix, prefix)
        for prefix in figure_prefixes
    }
    return all(
        not (_category_related_references(evidence, category) & cited)
        for category in figure_categories
    )


def _category_related_references(
    evidence: EvidenceBundle, category: str
) -> set[str]:
    """Return every allowed reference whose text identifies the given category.

    Matches broadly (substring, case-insensitive) so a legitimate but
    topically-adjacent reference — e.g. a dataset-catalog citation mentioning
    "shelters" when no real shelter records exist — is still treated as
    belonging to that absent category for this check.
    """
    return {
        ref
        for ref in EvidenceReferenceIndex.build(evidence)
        if category in ref.lower()
    }
