"""Behavioral tests for the evidence-only structured decision agent."""

import asyncio
from datetime import UTC, datetime
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.conversation.models import ConversationTurn
from backend.app.decision.exceptions import (
    DecisionCircuitOpenError,
    DecisionGenerationError,
    DecisionParsingError,
    DecisionProviderTimeoutError,
    DecisionRateLimitedError,
    DecisionSpecificityError,
    LLMOutputValidationError,
)
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
from backend.app.decision.agent import (
    OpenAIDecisionAgent,
    OpenAIDecisionProvider,
    _to_strict_openai_schema,
)
from backend.app.decision.parser import DecisionParser
from backend.app.decision.prompt_builder import PromptBuilder
from backend.app.decision.resilience import (
    DecisionCircuitBreaker,
    DecisionRuntimeConfig,
)
from backend.app.graph.nodes import RecommendationNode
from backend.app.graph.mappers import DecisionFallbackMapper
from backend.app.graph.state import (
    EvidenceBundle,
    EvidenceProvenance,
    ForecastEvidence,
    GISEvidence,
    KnowledgeEvidence,
    VillageEvidence,
)
from backend.tests.graph_test_support import state_factory


def _decision() -> Decision:
    """Create a complete valid decision for deterministic test scenarios."""
    return Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH, rationale="High discharge."
        ),
        recommendation=Recommendation(
            summary="Prepare local response.",
            actions=(
                ActionRecommendation(
                    action="Notify response teams.",
                    priority=Priority.HIGH,
                    evidence_references=("gis",),
                ),
            ),
            citations=("NDMA Plan:p4",),
            supporting_evidence=("gis",),
            missing_evidence=("shelter occupancy",),
        ),
        reasons=(DecisionReason(statement="GIS exposure is elevated."),),
        confidence=DecisionConfidence.HIGH,
    )


class _Completions:
    """Return deterministic structured responses while retaining request input."""

    def __init__(self, content: str | None) -> None:
        self.content = content
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        """Return one OpenAI-compatible completion shape."""
        self.requests.append(kwargs)
        return SimpleNamespace(
            choices=(SimpleNamespace(message=SimpleNamespace(content=self.content)),),
            usage=SimpleNamespace(total_tokens=42),
        )


class _TransientProviderError(Exception):
    """Represent a deterministic temporary provider failure for tests."""

    status_code = 503


class _RateLimitedProviderError(Exception):
    """Represent a deterministic provider rate-limit response for tests."""

    status_code = 429


class _Client:
    """Expose the narrow injected chat-completions surface used by the agent."""

    def __init__(self, completions: _Completions) -> None:
        self.chat = SimpleNamespace(completions=completions)


class _DecisionAgent:
    """Return one fixed decision while retaining the supplied evidence bundle."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        self.evidence = None
        self.execution_context = None
        self.current_request_text = None

    async def decide(self, evidence, *, execution_context=None, current_request_text=""):
        """Capture the canonical bundle and return the configured decision."""
        self.evidence = evidence
        self.execution_context = execution_context
        self.current_request_text = current_request_text
        return self.decision


@pytest.fixture
def parser_evidence() -> EvidenceBundle:
    """Provide citable evidence for parser schema-validation tests."""
    return EvidenceBundle(
        gis=GISEvidence(flood_zone="test-flood-zone"),
        knowledge=KnowledgeEvidence(citations=("NDMA Plan:p4",)),
        provenance=(
            EvidenceProvenance(evidence_type="gis", tool_name="GISAnalysisTool"),
        ),
    )


def test_decision_contract_is_frozen_and_rejects_unknown_fields() -> None:
    """Canonical decisions must remain strict immutable Pydantic contracts."""
    decision = _decision()

    with pytest.raises(ValidationError):
        decision.confidence = DecisionConfidence.LOW
    with pytest.raises(ValidationError):
        Decision.model_validate({**decision.model_dump(), "unexpected": True})


def test_strict_openai_schema_requires_all_object_properties() -> None:
    """OpenAI strict schemas must require every declared object property."""
    strict_schema = _to_strict_openai_schema(Decision.model_json_schema())
    object_schemas = (strict_schema, *strict_schema["$defs"].values())

    for schema in object_schemas:
        if "properties" not in schema:
            continue
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_parser_validates_structured_decision_json(
    parser_evidence: EvidenceBundle,
) -> None:
    """Parser should return the canonical decision for valid JSON only."""
    parsed = DecisionParser().parse(_decision().model_dump_json(), parser_evidence)

    assert parsed == _decision()


@pytest.mark.parametrize("response", ("not-json", "[]", '{"confidence":"high"}'))
def test_parser_rejects_malformed_or_invalid_decisions(
    response: str, parser_evidence: EvidenceBundle
) -> None:
    """Malformed JSON and schema failures must be domain-specific failures."""
    with pytest.raises((DecisionParsingError, LLMOutputValidationError)):
        DecisionParser().parse(response, parser_evidence)


def test_parser_raises_specificity_error_when_no_digits_are_used() -> None:
    """A Decision that ignores available quantitative figures must be rejected."""
    evidence = EvidenceBundle(
        gis=GISEvidence(flood_zone="high_risk", population_exposed=18000),
        provenance=(
            EvidenceProvenance(evidence_type="gis", tool_name="gis_domain_service"),
        ),
    )
    decision = Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH, rationale="There is a high risk of flooding."
        ),
        recommendation=Recommendation(
            summary="Prioritize alerting vulnerable populations.",
            citations=("gis",),
        ),
        reasons=(
            DecisionReason(
                statement="GIS exposure is elevated.", evidence_references=("gis",)
            ),
        ),
        confidence=DecisionConfidence.HIGH,
    )

    with pytest.raises(DecisionSpecificityError):
        DecisionParser().parse(decision.model_dump_json(), evidence)


def test_parser_accepts_decision_that_cites_a_quantitative_figure() -> None:
    """A Decision incorporating a real evidence number must pass validation."""
    evidence = EvidenceBundle(
        gis=GISEvidence(flood_zone="high_risk", population_exposed=18000),
        provenance=(
            EvidenceProvenance(evidence_type="gis", tool_name="gis_domain_service"),
        ),
    )
    decision = Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH,
            rationale="Approximately 18000 people are exposed in the flood zone.",
        ),
        recommendation=Recommendation(
            summary="Prioritize alerting vulnerable populations.",
            citations=("gis",),
        ),
        reasons=(
            DecisionReason(
                statement="GIS exposure is elevated.", evidence_references=("gis",)
            ),
        ),
        confidence=DecisionConfidence.HIGH,
    )

    parsed = DecisionParser().parse(decision.model_dump_json(), evidence)

    assert parsed == decision


def test_parser_skips_specificity_check_without_quantitative_evidence(
    parser_evidence: EvidenceBundle,
) -> None:
    """A knowledge-only bundle with no numeric evidence needs no digits."""
    parsed = DecisionParser().parse(_decision().model_dump_json(), parser_evidence)

    assert parsed == _decision()


def test_parser_skips_specificity_check_for_village_population_only_evidence() -> None:
    """Village population alone is context, not flood-severity evidence to cite."""
    evidence = EvidenceBundle(
        villages=(VillageEvidence(village_name="Kalam", population=12000),),
        provenance=(
            EvidenceProvenance(evidence_type="village", tool_name="village_tool"),
        ),
    )
    decision = Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.NORMAL,
            rationale="No evidence of flooding was found for this area.",
        ),
        recommendation=Recommendation(
            summary="No action needed at this time.",
            citations=("Kalam",),
        ),
        reasons=(
            DecisionReason(
                statement="Village population data was reviewed; no flood "
                "indicators are present.",
                evidence_references=("Kalam",),
            ),
        ),
        confidence=DecisionConfidence.HIGH,
    )

    parsed = DecisionParser().parse(decision.model_dump_json(), evidence)

    assert parsed == decision


def test_prompt_builder_is_deterministic_and_contains_only_bundle_and_schema() -> None:
    """Prompt construction should be repeatable with no provider interaction."""
    evidence = state_factory().create().evidence_bundle
    builder = PromptBuilder()

    first = builder.build(evidence)

    assert first == builder.build(evidence)
    assert "Decision schema" in first[0]
    assert "EvidenceBundle" in first[1]
    assert builder.PROMPT_VERSION == "v1.0.0"
    assert builder.SYSTEM_PROMPT_VERSION == "v1.0.0"


def test_prompt_builder_warns_against_citing_figure_labels() -> None:
    """The prompt must explicitly forbid citing 'Key quantitative figures' labels."""
    evidence = EvidenceBundle(
        gis=GISEvidence(flood_zone="high_risk", population_exposed=18000),
        villages=(VillageEvidence(village_name="Kabal", population=5000),),
        provenance=(
            EvidenceProvenance(evidence_type="gis", tool_name="gis_domain_service"),
        ),
    )
    builder = PromptBuilder()

    system_prompt, _ = builder.build(evidence)

    assert "NOT valid citations" in system_prompt


def test_prompt_builder_surfaces_stale_forecast_notice_for_missing_evidence() -> None:
    """A stale forecast must produce a missing_evidence-bound notice the user sees."""
    evidence = EvidenceBundle(
        forecast=ForecastEvidence(
            discharge=650.0,
            snapshot_stale=True,
            snapshot_age_hours=96.0,
        ),
    )
    builder = PromptBuilder()

    system_prompt, user_prompt = builder.build(evidence)

    assert "forecast (data is approximately 4 days old)" in user_prompt
    assert "Stale evidence notices" in system_prompt


def test_prompt_builder_omits_stale_notice_for_a_fresh_forecast() -> None:
    """A fresh forecast must not be reported as a stale evidence notice."""
    evidence = EvidenceBundle(
        forecast=ForecastEvidence(
            discharge=650.0,
            snapshot_stale=False,
            snapshot_age_hours=2.0,
        ),
    )
    builder = PromptBuilder()

    _, user_prompt = builder.build(evidence)

    assert "Stale evidence notices:\n[]" in user_prompt


def test_openai_provider_forwards_prior_turns_to_prompt_builder(
    parser_evidence: EvidenceBundle,
) -> None:
    """Provider must forward prior summaries and the current turn's own request text."""
    completions = _Completions(_decision().model_dump_json())
    provider = OpenAIDecisionProvider(
        client=_Client(completions),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
    )
    history = (
        ConversationTurn(
            request_text="Flood outlook for Mingora?",
            village_name="Mingora",
            evidence_bundle=parser_evidence,
            decision=_decision(),
            created_at=datetime(2026, 7, 28, tzinfo=UTC),
        ),
    )

    asyncio.run(
        provider.decide(
            parser_evidence,
            history=history,
            current_request_text="What about shelters?",
        )
    )

    user_prompt = completions.requests[0]["messages"][1]["content"]
    assert "Conversation history:" in user_prompt
    assert "Flood outlook for Mingora?" in user_prompt
    assert "Prepare local response." in user_prompt
    assert "Current request:" in user_prompt
    assert "What about shelters?" in user_prompt
    assert user_prompt.index("Conversation history:") < user_prompt.index(
        "Current request:"
    ) < user_prompt.index("EvidenceBundle:")


def test_openai_agent_name_remains_a_compatible_provider_alias() -> None:
    """Existing imports must resolve to the provider-oriented implementation."""
    assert OpenAIDecisionAgent is OpenAIDecisionProvider


def test_openai_agent_parses_mocked_schema_constrained_output(
    caplog, parser_evidence: EvidenceBundle
) -> None:
    """The provider adapter should return a parser-validated decision."""
    completions = _Completions(_decision().model_dump_json())
    caplog.set_level("INFO", logger="backend.app.decision.agent")
    agent = OpenAIDecisionProvider(
        client=_Client(completions),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
    )

    decision = asyncio.run(agent.decide(parser_evidence))

    assert decision == _decision()
    request = completions.requests[0]
    assert request["temperature"] == 0.0
    assert request["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "flood_aware_decision",
            "strict": True,
                "schema": _to_strict_openai_schema(Decision.model_json_schema()),
        },
    }
    completion_log = next(
        record
        for record in caplog.records
        if record.message == "decision_provider_request_finished"
    )
    assert completion_log.provider == "openai"
    assert completion_log.model == "gpt-4.1-mini"
    assert completion_log.retry_count == 0
    assert completion_log.timeout is False


def test_openai_agent_translates_provider_and_parser_failures() -> None:
    """Blank provider output and malformed decisions must never leak SDK failures."""
    blank_agent = OpenAIDecisionProvider(
        client=_Client(_Completions(None)),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
    )
    malformed_agent = OpenAIDecisionProvider(
        client=_Client(_Completions(json.dumps({"confidence": "high"}))),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
    )
    evidence = state_factory().create().evidence_bundle

    with pytest.raises(DecisionGenerationError):
        asyncio.run(blank_agent.decide(evidence))
    with pytest.raises(LLMOutputValidationError):
        asyncio.run(malformed_agent.decide(evidence))


def test_provider_retries_transient_failure_then_returns_decision(
    parser_evidence: EvidenceBundle,
) -> None:
    """A transient transport failure should retry without changing valid output."""
    completions = _Completions(_decision().model_dump_json())
    successful_create = completions.create
    calls = 0

    async def create(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _TransientProviderError()
        return await successful_create(**kwargs)

    client = _Client(completions)
    client.chat.completions.create = create
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=DecisionRuntimeConfig(retry_count=1, jitter_seconds=0),
        sleep=lambda _: asyncio.sleep(0),
    )

    assert (
        asyncio.run(provider.decide(parser_evidence))
        == _decision()
    )
    assert calls == 2


def test_provider_raises_after_persistent_rate_limit(
    parser_evidence: EvidenceBundle,
) -> None:
    """A persistent rate limit should fail after the configured retry budget."""
    calls = 0

    async def rate_limited(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise _RateLimitedProviderError()

    client = _Client(_Completions(_decision().model_dump_json()))
    client.chat.completions.create = rate_limited
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=DecisionRuntimeConfig(retry_count=1, jitter_seconds=0),
        sleep=lambda _: asyncio.sleep(0),
    )

    with pytest.raises(DecisionRateLimitedError):
        asyncio.run(provider.decide(parser_evidence))
    assert calls == 2


def test_provider_translates_timeout_and_recommendation_node_falls_back() -> None:
    """Timeout failures should be domain-safe and never terminate the graph path."""

    async def never_returns(**kwargs: object) -> object:
        await asyncio.sleep(1)
        raise AssertionError("unreachable")

    client = _Client(_Completions(_decision().model_dump_json()))
    client.chat.completions.create = never_returns
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=DecisionRuntimeConfig(
            timeout_seconds=0.001, retry_count=0, jitter_seconds=0
        ),
    )
    state = state_factory().create()

    with pytest.raises(DecisionProviderTimeoutError):
        asyncio.run(provider.decide(state.evidence_bundle))
    updated = asyncio.run(RecommendationNode(provider).execute(state))

    assert updated.recommendation.recommendation == "Decision generation unavailable."
    assert updated.recommendation.risk_level == "unknown"
    assert updated.recommendation.confidence == 0


def test_provider_retries_grounding_failure_with_correction_context_then_succeeds(
    parser_evidence: EvidenceBundle,
) -> None:
    """A grounding failure should retry with targeted correction, not an identical prompt."""
    invalid_decision = Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH, rationale="High discharge."
        ),
        recommendation=Recommendation(
            summary="Prepare local response.",
            citations=("shelter:Relief Camp Jail Road Mingora",),
        ),
        confidence=DecisionConfidence.HIGH,
    )
    responses = iter(
        (invalid_decision.model_dump_json(), _decision().model_dump_json())
    )
    requests: list[dict[str, object]] = []

    async def create(**kwargs: object) -> object:
        requests.append(kwargs)
        return SimpleNamespace(
            choices=(
                SimpleNamespace(message=SimpleNamespace(content=next(responses))),
            ),
            usage=SimpleNamespace(total_tokens=42),
        )

    client = _Client(_Completions(None))
    client.chat.completions.create = create
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=DecisionRuntimeConfig(retry_count=1, jitter_seconds=0),
        sleep=lambda _: asyncio.sleep(0),
    )

    assert asyncio.run(provider.decide(parser_evidence)) == _decision()
    assert len(requests) == 2

    first_messages = requests[0]["messages"]
    second_messages = requests[1]["messages"]
    assert len(first_messages) == 2
    assert len(second_messages) == 4
    assert second_messages[2] == {
        "role": "assistant",
        "content": invalid_decision.model_dump_json(),
    }
    assert second_messages[3]["role"] == "user"
    assert "shelter:Relief Camp Jail Road Mingora" in second_messages[3]["content"]


def test_provider_retries_non_grounding_failure_with_unchanged_messages(
    parser_evidence: EvidenceBundle,
) -> None:
    """Non-grounding failures must retry with the original prompt, unchanged."""
    completions = _Completions(_decision().model_dump_json())
    successful_create = completions.create
    calls = 0
    requests: list[dict[str, object]] = []

    async def create(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        requests.append(kwargs)
        if calls == 1:
            raise _RateLimitedProviderError()
        return await successful_create(**kwargs)

    client = _Client(completions)
    client.chat.completions.create = create
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=DecisionRuntimeConfig(retry_count=1, jitter_seconds=0),
        sleep=lambda _: asyncio.sleep(0),
    )

    assert asyncio.run(provider.decide(parser_evidence)) == _decision()
    assert calls == 2
    assert requests[0]["messages"] == requests[1]["messages"]
    assert len(requests[1]["messages"]) == 2


def test_provider_opens_circuit_after_retry_exhaustion_and_recovers(
    parser_evidence: EvidenceBundle,
) -> None:
    """Circuit opens after final transient failures and permits a recovery probe."""
    current_time = [0.0]
    config = DecisionRuntimeConfig(
        retry_count=0,
        jitter_seconds=0,
        circuit_breaker_threshold=1,
        circuit_recovery_seconds=10,
    )
    breaker = DecisionCircuitBreaker(config, clock=lambda: current_time[0])
    client = _Client(_Completions(_decision().model_dump_json()))

    async def unavailable(**kwargs: object) -> object:
        raise _RateLimitedProviderError()

    client.chat.completions.create = unavailable
    provider = OpenAIDecisionProvider(
        client=client,
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
        runtime_config=config,
        circuit_breaker=breaker,
    )
    evidence = parser_evidence

    with pytest.raises(DecisionGenerationError):
        asyncio.run(provider.decide(evidence))
    with pytest.raises(DecisionCircuitOpenError):
        asyncio.run(provider.decide(evidence))

    current_time[0] = 10.0
    client.chat.completions.create = _Completions(_decision().model_dump_json()).create
    assert asyncio.run(provider.decide(evidence)) == _decision()


@pytest.mark.parametrize(
    "configuration",
    (
        {"timeout_seconds": 0},
        {"retry_count": -1},
        {"circuit_breaker_threshold": 0},
    ),
)
def test_runtime_configuration_rejects_invalid_resilience_settings(
    configuration: dict[str, int],
) -> None:
    """Invalid resilience settings must fail before a provider is invoked."""
    with pytest.raises(ValueError):
        DecisionRuntimeConfig(**configuration)


def test_recommendation_node_consumes_only_bundle_and_updates_owned_section() -> None:
    """The graph node should project one agent decision without mutating state."""
    state = state_factory().create()
    agent = _DecisionAgent(_decision())

    updated = asyncio.run(RecommendationNode(agent).execute(state))

    assert agent.evidence is state.evidence_bundle
    assert agent.execution_context.execution_id == state.runtime.execution_id
    assert updated is not state
    assert updated.weather is state.weather
    assert updated.decision is agent.decision
    assert updated.recommendation.recommendation == "Prepare local response."
    assert updated.recommendation.recommended_actions == ("Notify response teams.",)
    assert updated.recommendation.missing_evidence == ("shelter occupancy",)


def test_recommendation_node_maps_decision_error_to_fallback() -> None:
    """A decision-agent failure should return the deterministic fallback evidence."""

    class _FailingDecisionAgent:
        async def decide(
            self, evidence, *, execution_context=None, current_request_text=""
        ):
            del evidence, execution_context, current_request_text
            raise DecisionRateLimitedError("Decision provider rate limit exceeded.")

    state = state_factory().create().model_copy(update={"decision": _decision()})
    updated = asyncio.run(RecommendationNode(_FailingDecisionAgent()).execute(state))

    assert updated.decision is None
    assert updated.recommendation == DecisionFallbackMapper.unavailable()


def test_evidence_bundle_to_agent_to_recommendation_evidence_flow(
    parser_evidence: EvidenceBundle,
) -> None:
    """Structured provider output should reach graph recommendation evidence intact."""
    state = state_factory().create().model_copy(
        update={"evidence_bundle": parser_evidence}
    )
    agent = OpenAIDecisionProvider(
        client=_Client(_Completions(_decision().model_dump_json())),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model="gpt-4.1-mini",
    )

    updated = asyncio.run(RecommendationNode(agent).execute(state))

    assert updated.decision is not None
    assert updated.recommendation.risk_level == "high"
    assert updated.recommendation.recommendation == "Prepare local response."
    assert updated.recommendation.citations == ("NDMA Plan:p4",)
    assert updated.recommendation.supporting_evidence == ("gis",)
