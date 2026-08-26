"""Behavioral tests for real-time, non-small-talk intent classification."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.app.conversation.exceptions import IntentClassificationError
from backend.app.conversation.intent import (
    IntentClassification,
    IntentLabel,
    IntentPromptBuilder,
    OpenAIIntentClassifier,
    _strict_schema,
)
from backend.app.conversation.models import ConversationMode, ConversationTurn
from backend.app.graph.state import EvidenceBundle
from datetime import UTC, datetime


class _Completions:
    """Return a scripted response, or sleep/raise, while retaining every request."""

    def __init__(
        self,
        content: str | None = None,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.content = content
        self.error = error
        self.delay_seconds = delay_seconds
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        """Record one request and return, sleep, or raise as scripted."""
        self.requests.append(kwargs)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=(SimpleNamespace(message=SimpleNamespace(content=self.content)),)
        )


class _Client:
    """Expose the narrow injected chat-completions surface used by the classifier."""

    def __init__(self, completions: _Completions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def _turn(request_text: str, summary: str) -> ConversationTurn:
    """Create a minimal recorded turn for history-rendering assertions."""
    return ConversationTurn(
        request_text=request_text,
        evidence_bundle=EvidenceBundle(),
        summary=summary,
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def _valid_content(label: str, response_text: str = "") -> str:
    return json.dumps({"label": label, "response_text": response_text})


def test_prompt_builder_uses_mode_specific_capabilities() -> None:
    """The classifier must ground capability answers in the right product's facts."""
    builder = IntentPromptBuilder()

    flood_system, _ = builder.build("hi there", mode=ConversationMode.FLOOD_AGENT)
    policy_system, _ = builder.build("hi there", mode=ConversationMode.POLICY_ADVISOR)

    assert "Swat district" in flood_system
    assert "PDMA/NDMP" in policy_system
    assert flood_system != policy_system


def test_prompt_builder_omits_history_section_when_empty() -> None:
    """No prior turns must mean no history section, matching the decision prompt builder."""
    _, user_prompt = IntentPromptBuilder().build(
        "How can you help?", mode=ConversationMode.FLOOD_AGENT
    )

    assert "Conversation history:" not in user_prompt
    assert "Current message:\nHow can you help?" in user_prompt


def test_prompt_builder_includes_prior_turns_when_present() -> None:
    """Prior turns must be visible so a clarifying question is not repeated."""
    turn = _turn("Is it safe?", "Which village would you like me to assess?")

    _, user_prompt = IntentPromptBuilder().build(
        "Mingora", mode=ConversationMode.FLOOD_AGENT, history=(turn,)
    )

    assert "Conversation history:" in user_prompt
    assert "Is it safe?" in user_prompt
    assert "Which village would you like me to assess?" in user_prompt
    assert user_prompt.index("Conversation history:") < user_prompt.index(
        "Current message:"
    )


def test_prompt_builder_states_when_a_location_is_already_resolved() -> None:
    """The classifier must be told directly, not left to infer it from prior text.

    Regression guard for the false-positive bug where a real follow-up in an
    established conversation (e.g. "What about shelters?" after a village
    was already selected) was wrongly classified as needing a location,
    because the classifier had no direct signal that one was already
    resolved on the current request.
    """
    _, resolved_prompt = IntentPromptBuilder().build(
        "What about shelters?", mode=ConversationMode.FLOOD_AGENT, has_location=True
    )
    _, unresolved_prompt = IntentPromptBuilder().build(
        "What about shelters?", mode=ConversationMode.FLOOD_AGENT, has_location=False
    )

    assert "Location already provided: true" in resolved_prompt
    assert "Location already provided: false" in unresolved_prompt


def test_prompt_builder_omits_location_line_for_policy_advisor() -> None:
    """Policy Advisor has no location concept -- the line must never appear there."""
    _, user_prompt = IntentPromptBuilder().build(
        "Tell me about policy.",
        mode=ConversationMode.POLICY_ADVISOR,
        has_location=True,
    )

    assert "Location already provided" not in user_prompt


def test_classify_parses_a_valid_structured_response() -> None:
    """A well-formed structured response must parse into the typed classification."""
    completions = _Completions(
        _valid_content("capability_question", "I assess flood risk in Swat district.")
    )
    classifier = OpenAIIntentClassifier(
        client=_Client(completions),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
    )

    result = asyncio.run(
        classifier.classify("How can you help me?", mode=ConversationMode.FLOOD_AGENT)
    )

    assert result == IntentClassification(
        label=IntentLabel.CAPABILITY_QUESTION,
        response_text="I assess flood risk in Swat district.",
    )
    request = completions.requests[0]
    assert request["model"] == "gpt-4.1-mini"
    assert request["response_format"]["json_schema"]["strict"] is True


def test_classify_raises_on_empty_content() -> None:
    """Blank structured content must never be treated as an implicit classification."""
    classifier = OpenAIIntentClassifier(
        client=_Client(_Completions("")),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
    )

    with pytest.raises(IntentClassificationError):
        asyncio.run(
            classifier.classify("hello", mode=ConversationMode.FLOOD_AGENT)
        )


def test_classify_raises_on_malformed_json() -> None:
    """Non-JSON structured content must translate to a classification error."""
    classifier = OpenAIIntentClassifier(
        client=_Client(_Completions("not json")),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
    )

    with pytest.raises(IntentClassificationError):
        asyncio.run(
            classifier.classify("hello", mode=ConversationMode.FLOOD_AGENT)
        )


def test_classify_raises_on_schema_violation() -> None:
    """Valid JSON that violates the classification contract must still fail closed."""
    completions = _Completions(json.dumps({"label": "not_a_real_label"}))
    classifier = OpenAIIntentClassifier(
        client=_Client(completions),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
    )

    with pytest.raises(IntentClassificationError):
        asyncio.run(
            classifier.classify("hello", mode=ConversationMode.FLOOD_AGENT)
        )


def test_classify_raises_on_provider_exception() -> None:
    """Any underlying client failure must translate uniformly, never leak or crash."""
    classifier = OpenAIIntentClassifier(
        client=_Client(_Completions(error=ConnectionError("network down"))),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
    )

    with pytest.raises(IntentClassificationError):
        asyncio.run(
            classifier.classify("hello", mode=ConversationMode.FLOOD_AGENT)
        )


def test_classify_raises_on_timeout() -> None:
    """A slow provider must be bounded, never hang the conversation turn."""
    classifier = OpenAIIntentClassifier(
        client=_Client(_Completions(_valid_content("genuine_question"), delay_seconds=0.2)),
        prompt_builder=IntentPromptBuilder(),
        model="gpt-4.1-mini",
        timeout_seconds=0.01,
    )

    with pytest.raises(IntentClassificationError):
        asyncio.run(
            classifier.classify("hello", mode=ConversationMode.FLOOD_AGENT)
        )


def test_strict_schema_requires_every_property_and_forbids_extras() -> None:
    """The structured-output schema must match this project's OpenAI strict-mode contract."""
    schema = _strict_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
