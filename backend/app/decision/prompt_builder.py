"""Deterministic prompt construction from canonical evidence only."""

import json
from collections.abc import Sequence
from typing import ClassVar

from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.models import Decision
from backend.app.decision.protocols import ConversationTurnLike
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
        "SPECIFICITY: When 'Key quantitative figures' is non-empty, "
        "`risk_assessment.rationale` and at least one entry in `reasons` must "
        "incorporate at least one concrete figure from that list — not just "
        "name the evidence category, but state the actual number. You may "
        "round large figures for readability, but the number must come from "
        "the real evidence, never be invented.\n\n"
        "Weak, generic rationale (do not write like this): \"There is a high "
        "risk of flooding due to major flood zone designation and large "
        "population exposure.\"\n\n"
        "Strong, specific rationale (write like this): \"The area is "
        "classified as a major flood zone with approximately 695,600 people "
        "exposed and 4 critical infrastructure assets at risk, based on GIS "
        "analysis.\"\n\n"
        "The labels in 'Key quantitative figures' (e.g. 'gis.population_exposed', "
        "'village.Kabal.population') describe what the numbers mean for your "
        "reasoning only — they are NOT valid citations. Never place a figure "
        "label in citations, supporting_evidence, or evidence_references. Only "
        "strings from 'Allowed citation values' may be used there; if a figure "
        "needs a citation, cite the evidence section or entity it came from "
        "(e.g. cite 'gis' or the specific village name, not the figure label "
        "itself).\n\n"
        "CONVERSATION HISTORY: Prior turns provide continuity only. Apply all "
        "grounding and citation rules exclusively to the current EvidenceBundle; "
        "never cite prior-turn evidence as current evidence.\n\n"
        "Return only JSON that validates against the supplied schema."
    )

    def build(
        self,
        evidence: EvidenceBundle,
        *,
        history: Sequence[ConversationTurnLike] = (),
    ) -> tuple[str, str]:
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
        history_section = _conversation_history_section(history)
        key_figures_json = json.dumps(_key_figures(evidence), sort_keys=True)
        user_prompt = (
            f"{history_section}"
            f"EvidenceBundle:\n{evidence_json}\n\n"
            f"Key quantitative figures (use these in your reasoning):\n"
            f"{key_figures_json}\n\n"
            f"Allowed citation values (use these exact strings only):\n"
            f"{allowed_refs_json}\n\n"
            f"Unresolved evidence conflicts:\n{conflicts_json}\n\n"
            f"Entirely absent evidence categories:\n{absent_categories_json}"
        )
        return system_prompt, user_prompt


def _key_figures(evidence: EvidenceBundle) -> dict[str, str]:
    """Return real quantitative evidence values in human-readable form."""
    figures: dict[str, str] = {}
    if evidence.forecast.discharge is not None:
        figures["forecast.discharge_m3_per_second"] = str(evidence.forecast.discharge)
    if evidence.forecast.lead_time is not None:
        figures["forecast.lead_time_hours"] = str(evidence.forecast.lead_time)
    if evidence.gis.population_exposed is not None:
        figures["gis.population_exposed"] = str(evidence.gis.population_exposed)
    if evidence.gis.infrastructure_exposed is not None:
        figures["gis.infrastructure_exposed"] = str(evidence.gis.infrastructure_exposed)
    if evidence.gis.affected_area is not None:
        figures["gis.affected_area_square_meters"] = str(evidence.gis.affected_area)
    if evidence.weather.rainfall is not None:
        figures["weather.rainfall_mm"] = str(evidence.weather.rainfall)
    if evidence.weather.temperature is not None:
        figures["weather.temperature_celsius"] = str(evidence.weather.temperature)
    if evidence.shelters.available_capacity is not None:
        figures["shelters.available_capacity"] = str(evidence.shelters.available_capacity)
    for village in evidence.villages:
        if village.population is not None and village.village_name:
            figures[f"village.{village.village_name}.population"] = str(village.population)
    return figures


def _flood_severity_figures(evidence: EvidenceBundle) -> dict[str, str]:
    """Return only the flood-severity-relevant quantitative evidence values.

    Village population is deliberately excluded: it is useful reasoning
    context but is not, on its own, evidence of flood severity, so it must
    never force a specificity requirement.
    """
    figures: dict[str, str] = {}
    if evidence.forecast.discharge is not None:
        figures["forecast.discharge_m3_per_second"] = str(evidence.forecast.discharge)
    if evidence.forecast.lead_time is not None:
        figures["forecast.lead_time_hours"] = str(evidence.forecast.lead_time)
    if evidence.gis.population_exposed is not None:
        figures["gis.population_exposed"] = str(evidence.gis.population_exposed)
    if evidence.gis.infrastructure_exposed is not None:
        figures["gis.infrastructure_exposed"] = str(evidence.gis.infrastructure_exposed)
    if evidence.gis.affected_area is not None:
        figures["gis.affected_area_square_meters"] = str(evidence.gis.affected_area)
    if evidence.weather.rainfall is not None:
        figures["weather.rainfall_mm"] = str(evidence.weather.rainfall)
    if evidence.weather.temperature is not None:
        figures["weather.temperature_celsius"] = str(evidence.weather.temperature)
    if evidence.shelters.available_capacity is not None:
        figures["shelters.available_capacity"] = str(evidence.shelters.available_capacity)
    return figures


def _conversation_history_section(history: Sequence[ConversationTurnLike]) -> str:
    """Render bounded prior-turn continuity context without prior evidence."""
    if not history:
        return ""
    turns = [
        {
            "request_text": turn.request_text,
            "recommendation_summary": turn.recommendation_summary,
        }
        for turn in history
    ]
    return "Conversation history:\n" + json.dumps(
        turns, sort_keys=True, separators=(",", ":")
    ) + "\n\n"


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
