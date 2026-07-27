"""Deterministic prompt construction from canonical evidence only."""

import json
from typing import ClassVar

from backend.app.decision.models import Decision
from backend.app.graph.state import EvidenceBundle
from backend.app.observability.version import PROMPT_VERSION, SYSTEM_VERSION


class PromptBuilder:
    """Build deterministic, provider-independent prompts from an evidence bundle.

    The builder is pure: it neither calls a provider, parses output, nor produces
    a decision. Version metadata is intentionally separate from rendered prompt
    content so prompt behaviour remains stable while evaluations can identify it.
    """

    PROMPT_VERSION: ClassVar[str] = PROMPT_VERSION
    SYSTEM_PROMPT_VERSION: ClassVar[str] = PROMPT_VERSION
    SYSTEM_VERSION: ClassVar[str] = SYSTEM_VERSION

    _SYSTEM_INSTRUCTIONS = (
        "You are Flood-Aware's evidence-grounded flood decision agent. "
        "Use only the supplied EvidenceBundle. Do not invent facts, sources, "
        "or actions. Identify missing evidence explicitly. Return only JSON "
        "that validates against the supplied schema."
    )

    def build(self, evidence: EvidenceBundle) -> tuple[str, str]:
        """Return deterministic system and user prompts for one evidence bundle."""
        schema = json.dumps(
            Decision.model_json_schema(), sort_keys=True, separators=(",", ":")
        )
        evidence_json = json.dumps(
            evidence.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return (
            f"{self._SYSTEM_INSTRUCTIONS}\nDecision schema:\n{schema}",
            f"EvidenceBundle:\n{evidence_json}",
        )


# TODO(post-MVP): Compare versioned prompts through controlled evaluation and
# A/B testing without changing this deterministic prompt-construction boundary.
