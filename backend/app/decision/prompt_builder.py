"""Deterministic prompt construction from canonical evidence only."""

import json
from typing import ClassVar

from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.models import Decision
from backend.app.graph.state import (
    EvidenceBundle,
    ForecastEvidence,
    GISEvidence,
    KnowledgeEvidence,
    WeatherEvidence,
)
from backend.app.observability.version import PROMPT_VERSION, SYSTEM_VERSION


class PromptBuilder:
    """Build deterministic, provider-independent prompts from an evidence bundle."""

    PROMPT_VERSION: ClassVar[str] = PROMPT_VERSION
    SYSTEM_PROMPT_VERSION: ClassVar[str] = PROMPT_VERSION
    SYSTEM_VERSION: ClassVar[str] = SYSTEM_VERSION

    _SYSTEM_INSTRUCTIONS = (
        "You are Flood-Aware's evidence-grounded flood decision agent. "
        "Use only the supplied EvidenceBundle. Do not invent facts, sources, "
        "actions, or citations.\n\n"
        "CITATIONS: Every entry in `citations`, `supporting_evidence`, and "
        "`evidence_references` must be copied EXACTLY, character-for-character, "
        "from the 'Allowed citation values' list below. Never invent a new "
        "string, paraphrase one, or combine two. If you cannot support a claim "
        "with one of the allowed values, do not make the claim. When both a "
        "specific named entity (a village or shelter name) and a generic "
        "tool-level reference are valid citations for the same claim, prefer "
        "citing the specific named entity.\n\n"
        "GROUNDING: If evidence exists relevant to the request, "
        "`recommendation.citations` must be non-empty and each "
        "`reasons[i].evidence_references` must be non-empty. If the bundle is "
        "empty or irrelevant, say so in `recommendation.missing_evidence` "
        "instead of fabricating support.\n\n"
        "CONFLICTS: If 'Unresolved evidence conflicts' below is non-empty, you "
        "must: (1) set `confidence` no higher than 'medium', (2) reference the "
        "conflicting subject in `recommendation.missing_evidence`, and (3) "
        "explain the disagreement in `risk_assessment.rationale` instead of "
        "silently picking one value.\n\n"
        "COMPLETENESS: Every category listed in 'Entirely absent evidence "
        "categories' must be explicitly named in `recommendation.missing_evidence`, "
        "regardless of whether other evidence seems sufficient to act on. Category "
        "names listed under 'Entirely absent evidence categories' must never appear "
        "in `citations`, `supporting_evidence`, or `evidence_references`; they are "
        "missing, not citable. Only strings from 'Allowed citation values' may be "
        "used there.\n\n"
        "SINGLE-SOURCE CONFIDENCE: Do not assign confidence 'high' when your "
        "assessment rests on only one evidence category, especially when the "
        "forecast category (the authoritative hydrological source) is absent. "
        "Reserve 'high' confidence for cases corroborated by at least two "
        "independent evidence categories, or by forecast data alone when it is "
        "present and unambiguous.\n\n"
        "Return only JSON that validates against the supplied schema."
    )

    def build(self, evidence: EvidenceBundle) -> tuple[str, str]:
        """Return deterministic system and user prompts for one evidence bundle."""
        schema = json.dumps(
            Decision.model_json_schema(), sort_keys=True, separators=(",", ":")
        )
        evidence_json = json.dumps(
            evidence.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        allowed_refs = sorted(EvidenceReferenceIndex.build(evidence))
        allowed_refs_json = json.dumps(allowed_refs, sort_keys=True)
        absent_categories_json = json.dumps(
            sorted(_entirely_absent_evidence_categories(evidence))
        )
        conflicts_json = json.dumps(
            [c.model_dump(mode="json") for c in evidence.conflicts],
            sort_keys=True,
            separators=(",", ":"),
        )

        system_prompt = f"{self._SYSTEM_INSTRUCTIONS}\nDecision schema:\n{schema}"
        user_prompt = (
            f"EvidenceBundle:\n{evidence_json}\n\n"
            f"Allowed citation values (use these exact strings only):\n"
            f"{allowed_refs_json}\n\n"
            f"Unresolved evidence conflicts:\n{conflicts_json}\n\n"
            f"Entirely absent evidence categories:\n{absent_categories_json}"
        )
        return system_prompt, user_prompt


def _entirely_absent_evidence_categories(evidence: EvidenceBundle) -> set[str]:
    """Return major evidence categories whose sections contain no evidence."""
    absent: set[str] = set()
    if evidence.forecast == ForecastEvidence():
        absent.add("forecast")
    if evidence.gis == GISEvidence():
        absent.add("gis")
    if evidence.weather == WeatherEvidence():
        absent.add("weather")
    if evidence.knowledge == KnowledgeEvidence():
        absent.add("knowledge")
    return absent
