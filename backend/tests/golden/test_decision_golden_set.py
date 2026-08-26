"""Golden-set evaluation of real LLM decisions. Costs real API calls."""

from datetime import UTC, datetime
import os
import re

import pytest

from backend.app.conversation.models import ConversationTurn
from backend.app.decision.dependencies import build_openai_decision_provider
from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.models import (
    ActionRecommendation,
    Decision,
    DecisionConfidence,
    DecisionReason,
    Priority,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)
from backend.tests.golden import fixtures as f

_INVENTED_SPECIFIC_PATTERN = re.compile(
    r"\d|has capacity of|\bis ready\b", re.IGNORECASE
)

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

    async def test_extreme_exposure_reasoning_cites_concrete_figures(self, provider):
        decision = await provider.decide(f.scenario_extreme_exposure())
        text = " ".join(
            (
                decision.risk_assessment.rationale,
                decision.recommendation.summary,
                *(reason.statement for reason in decision.reasons),
            )
        )
        assert re.search(r"\d{2,}", text)

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

    async def test_shelter_specific_question_without_shelter_data_succeeds(
        self, provider
    ):
        """Live-observed failure: a question specifically about the absent
        'shelter' category must not exhaust the grounding-retry budget and
        503. Reproduces the real session pattern -- a follow-up turn whose
        *current request* itself asks about shelters ("What shelters are
        available...") right after a general flood-outlook turn, while
        ShelterEvidence is entirely absent. A successful return here (no
        DecisionActionGroundingError propagating out of `decide`) is itself
        proof retries did not exhaust; missing_evidence must still name
        'shelter' honestly, and no action may fabricate shelter specifics.
        """
        bundle = f.scenario_shelter_question_no_shelter_data()
        prior_turn = ConversationTurn(
            request_text="What is the flood outlook for Mingora?",
            village_name="Mingora",
            evidence_bundle=bundle,
            decision=Decision(
                risk_assessment=RiskAssessment(
                    level=RiskLevel.MODERATE,
                    rationale="Moderate discharge with high-risk GIS exposure.",
                ),
                recommendation=Recommendation(
                    summary="Monitor conditions and prepare for possible evacuation.",
                    actions=(
                        ActionRecommendation(
                            action="Continue monitoring river discharge.",
                            priority=Priority.MEDIUM,
                            evidence_references=("forecast",),
                        ),
                    ),
                    citations=("forecast", "gis"),
                    supporting_evidence=("forecast", "gis"),
                ),
                reasons=(
                    DecisionReason(
                        statement="Discharge and GIS exposure indicate moderate risk.",
                        evidence_references=("forecast", "gis"),
                    ),
                ),
                confidence=DecisionConfidence.MEDIUM,
            ),
            summary="Monitor conditions and prepare for possible evacuation.",
            created_at=datetime(2026, 7, 27, tzinfo=UTC),
        )

        decision = await provider.decide(
            bundle,
            history=(prior_turn,),
            current_request_text=(
                "What shelters are available near Mingora, and are they "
                "ready for evacuees?"
            ),
        )

        missing = " ".join(decision.recommendation.missing_evidence).lower()
        assert "shelter" in missing

        # Mentioning "shelter" by name is honest and expected here -- the
        # question is about shelters. What's disqualifying is an INVENTED
        # specific (a number, or a definitive, unearned status claim), not
        # the topic word itself. Acknowledge/gather language like "Obtain
        # shelter data" or "assess shelter capacity before finalizing
        # evacuation planning" must remain allowed, matching the same
        # standard parser.py's _validate_no_actions_on_absent_categories
        # already enforces (specific-claim language grounded only in an
        # absent category, not mere mention of the category).
        for action in decision.recommendation.actions:
            assert not _INVENTED_SPECIFIC_PATTERN.search(action.action), (
                "Action invents a concrete shelter specific (a number or a "
                "definitive status claim) despite shelter evidence being "
                f"absent: {action.action!r}"
            )

    async def test_shelter_specific_question_does_not_trigger_specificity_error(
        self, provider
    ):
        """Live-observed failure (captured log): failure_type=
        DecisionSpecificityError, attempt_count=3, retry_count=2, followed
        by decision_generation_fallback_used and a 503. Root cause:
        _validate_specificity required a quantitative figure to appear
        somewhere in the response even when the only figures available
        (forecast/GIS/weather) are unrelated to a current request that is
        specifically about the entirely-absent 'shelter' category, and the
        honest answer for that absent category has nothing quantitative to
        report. This must now succeed and still honestly name the absent
        category in missing_evidence, without weakening the check for a
        response that genuinely ignores present, cited figures.
        """
        bundle = f.scenario_shelter_question_no_shelter_data()
        prior_turn = ConversationTurn(
            request_text="What is the flood outlook for Mingora?",
            village_name="Mingora",
            evidence_bundle=bundle,
            decision=Decision(
                risk_assessment=RiskAssessment(
                    level=RiskLevel.MODERATE,
                    rationale="Moderate discharge of 1400 m3/s with high-risk GIS exposure.",
                ),
                recommendation=Recommendation(
                    summary="Monitor conditions and prepare for possible evacuation.",
                    actions=(
                        ActionRecommendation(
                            action="Continue monitoring river discharge.",
                            priority=Priority.MEDIUM,
                            evidence_references=("forecast",),
                        ),
                    ),
                    citations=("forecast", "gis"),
                    supporting_evidence=("forecast", "gis"),
                ),
                reasons=(
                    DecisionReason(
                        statement="Discharge of 1400 m3/s and high GIS exposure indicate moderate risk.",
                        evidence_references=("forecast", "gis"),
                    ),
                ),
                confidence=DecisionConfidence.MEDIUM,
            ),
            summary="Monitor conditions and prepare for possible evacuation.",
            created_at=datetime(2026, 7, 27, tzinfo=UTC),
        )

        decision = await provider.decide(
            bundle,
            history=(prior_turn,),
            current_request_text="What shelters are available near Mingora?",
        )

        missing = " ".join(decision.recommendation.missing_evidence).lower()
        assert "shelter" in missing

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
