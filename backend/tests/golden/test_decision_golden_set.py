"""Golden-set evaluation of real LLM decisions. Costs real API calls."""

import os

import pytest

from backend.app.decision.dependencies import build_openai_decision_provider
from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.models import Decision, DecisionConfidence, RiskLevel, Priority
from backend.tests.golden import fixtures as f

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_GOLDEN_SET") != "1",
        reason="Golden-set tests call the real OpenAI API; set RUN_GOLDEN_SET=1 to run.",
    ),
]


def _all_references(decision: Decision) -> set[str]:
    """Collect every citation-like reference from a Decision, all fields."""
    references = set(decision.recommendation.citations)
    references.update(decision.recommendation.supporting_evidence)
    for item in (*decision.recommendation.actions, *decision.reasons):
        references.update(item.evidence_references)
    return references


@pytest.fixture(scope="module")
def provider():
    """Build a real, unmocked OpenAIDecisionProvider for golden-set runs."""
    # Reuse whatever composition-root factory already wires this for
    # production — do NOT hand-construct the client here if one exists.
    return build_openai_decision_provider()


class TestGoldenSet:
    async def test_severe_forecast_gis(self, provider):
        decision = await provider.decide(f.scenario_severe_forecast_gis())
        assert decision.risk_assessment.level in {RiskLevel.HIGH, RiskLevel.EXTREME}
        assert decision.recommendation.citations
        assert any(
            a.priority in {Priority.HIGH, Priority.CRITICAL}
            for a in decision.recommendation.actions
        )

    async def test_calm_baseline(self, provider):
        decision = await provider.decide(f.scenario_calm_baseline())
        assert decision.risk_assessment.level in {RiskLevel.NORMAL, RiskLevel.LOW}
        assert decision.confidence != DecisionConfidence.LOW

    async def test_conflicting_severity_downgrades_confidence(self, provider):
        decision = await provider.decide(f.scenario_conflicting_severity())
        assert decision.confidence in {DecisionConfidence.LOW, DecisionConfidence.MEDIUM}
        conflict_keywords = (
            "conflict",
            "disagree",
            "inconsist",
            "discrepanc",
            "differ",
        )
        text = (
            decision.risk_assessment.rationale
            + " ".join(decision.recommendation.missing_evidence)
        ).lower()
        assert any(keyword in text for keyword in conflict_keywords)

    async def test_empty_bundle_is_honest(self, provider):
        decision = await provider.decide(f.scenario_empty_bundle())
        assert decision.recommendation.citations == ()
        assert decision.recommendation.missing_evidence

    async def test_shelter_recommendation(self, provider):
        shelter = "Al-Noor Community Shelter"
        decision = await provider.decide(f.scenario_shelter_recommendation())
        references = _all_references(decision)
        assert shelter in references or "shelter:shelter_tool" in references

    async def test_knowledge_only(self, provider):
        bundle = f.scenario_knowledge_only()
        decision = await provider.decide(bundle)
        allowed = EvidenceReferenceIndex.build(bundle)
        assert set(decision.recommendation.citations).issubset(allowed)

    async def test_extreme_exposure(self, provider):
        decision = await provider.decide(f.scenario_extreme_exposure())
        assert decision.risk_assessment.level == RiskLevel.EXTREME
        assert any(
            action.priority == Priority.CRITICAL
            for action in decision.recommendation.actions
        )

    async def test_weather_only(self, provider):
        decision = await provider.decide(f.scenario_weather_only())
        assert decision.confidence != DecisionConfidence.HIGH
        forecast_keywords = (
            "forecast",
            "hydrolog",
            "discharge",
            "glofas",
            "river level",
        )
        text = " ".join(decision.recommendation.missing_evidence).lower()
        assert any(keyword in text for keyword in forecast_keywords)

    async def test_multiple_villages(self, provider):
        villages = {"Kot Addu", "Jhang", "Charsadda"}
        decision = await provider.decide(f.scenario_multiple_villages())
        references = _all_references(decision)
        village_level_cited = any("village" in ref.lower() for ref in references)
        assert (references & villages) or village_level_cited

    async def test_capacity_shortfall(self, provider):
        bundle = f.scenario_capacity_shortfall()
        decision = await provider.decide(bundle)
        references = _all_references(decision)
        allowed = EvidenceReferenceIndex.build(bundle)
        shelter_related = {
            ref
            for ref in allowed
            if "shelter" in ref.lower()
            or ref in bundle.shelters.shelters
            or ref == bundle.shelters.nearest_shelter
        }
        assert references & shelter_related

    async def test_duplicate_evidence(self, provider):
        decision = await provider.decide(f.scenario_duplicate_evidence())
        assert decision.recommendation.citations

    async def test_full_bundle(self, provider):
        decision = await provider.decide(f.scenario_full_bundle())
        references = _all_references(decision)
        sections = {
            "weather",
            "forecast",
            "gis",
            "village",
            "shelter",
            "knowledge",
            "dataset",
        }
        matched_sections = {
            section
            for section in sections
            if any(section in ref.lower() for ref in references)
        }
        assert len(matched_sections) >= 4
