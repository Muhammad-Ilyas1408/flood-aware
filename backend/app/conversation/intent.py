"""Real-time intent classification for turns that miss the small-talk phrase list.

Runs only after ``small_talk.is_small_talk`` has already returned ``False``:
that deterministic, zero-cost check remains the sole authority for
greetings/thanks/farewells (Hotfix 19), unchanged. This module exists to
distinguish, among everything else a user might type, three kinds of turn
that must not all be forced through the same heavy pipeline:

- A capability/meta question ("how can you help me?", "what can I ask you?")
  -- answered directly, grounded only in this product's real, fixed
  capabilities, never in flood evidence or retrieved policy text.
- A genuinely ambiguous or too-vague request -- answered with one real
  clarifying question, rather than guessing or running the full pipeline
  speculatively.
- A genuine, specific question -- left entirely alone, falling through to
  the existing flood-decision or RAG pipeline unchanged.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from enum import Enum
from typing import Protocol, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.conversation.exceptions import IntentClassificationError
from backend.app.conversation.models import ConversationMode

if TYPE_CHECKING:
    from backend.app.decision.protocols import ConversationTurnLike


class IntentLabel(str, Enum):
    """Classify a non-small-talk turn into one of three routing outcomes."""

    CAPABILITY_QUESTION = "capability_question"
    NEEDS_CLARIFICATION = "needs_clarification"
    GENUINE_QUESTION = "genuine_question"


class IntentClassification(BaseModel):
    """Represent one classified turn, with generated text where applicable.

    ``response_text`` is always a string rather than ``str | None``: an
    empty string means "not applicable" (the ``GENUINE_QUESTION`` case),
    which keeps the OpenAI strict structured-output schema flat and avoids
    a nullable-field union for a single optional field.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: IntentLabel
    response_text: str = ""


class IntentClassifierProtocol(Protocol):
    """Provider abstraction for classifying one conversation turn's intent."""

    async def classify(
        self,
        request_text: str,
        *,
        mode: ConversationMode,
        history: Sequence[ConversationTurnLike] = (),
        has_location: bool = False,
    ) -> IntentClassification:
        """Return a classification for one turn already known not to be small talk."""


_FLOOD_AGENT_CAPABILITIES = (
    "Flood Guide assesses flood risk for specific villages in Swat "
    "district. It needs a village or coordinates to run, and answers using "
    "live weather, river-forecast (GloFAS), GIS flood-zone/population/"
    "infrastructure analysis, and shelter data -- never general knowledge "
    "or speculation. It cannot assess areas outside Swat district, and "
    "cannot answer non-flood questions (for those, Policy Advisor handles "
    "government policy and disaster-management guidance)."
)

_POLICY_ADVISOR_CAPABILITIES = (
    "Policy Advisor answers questions about government flood policy, "
    "disaster-management plans, and official evacuation guidance, grounded "
    "only in retrieved passages from real PDMA/NDMP documents. It never "
    "assesses live flood risk for a specific location, and never uses "
    "weather, forecast, or GIS data -- for that, Flood Guide handles "
    "location-specific flood-risk questions."
)

_SYSTEM_INSTRUCTIONS = (
    "You classify one user message sent to a flood-disaster-response "
    "assistant. The message is already confirmed NOT to be a greeting, "
    "thanks, or farewell -- do not reconsider that.\n\n"
    "Classify it into exactly one label:\n\n"
    "capability_question -- the user is asking what this assistant can do, "
    "how to use it, or what kinds of things they can ask it (e.g. \"how can "
    "you help me?\", \"what can I ask you?\", \"how does this work?\"). They "
    "are asking about the ASSISTANT, not about flood risk or policy "
    "content. Set response_text to a genuine, specific answer describing "
    "this product's real capabilities below -- never invent a capability "
    "not listed, never answer the substance of a flood or policy "
    "question here.\n\n"
    "needs_clarification -- the message has NO discernible subject at all: "
    "no named location, no named topic, and nothing inheritable from "
    "established conversation history. Set response_text to ONE specific, "
    "genuine clarifying question that would let the assistant give a real "
    "answer once the user responds. response_text MUST be phrased as an "
    "actual question ending in '?' -- never a statement or instruction "
    "(write \"Which village or coordinates would you like me to assess?\", "
    "never \"Please specify the village.\"). Check conversation history "
    "first -- never repeat a clarifying question already asked; if the "
    "user's message plausibly answers a clarifying question from the "
    "immediately preceding turn, prefer genuine_question instead. If "
    "'Location already provided' below is true, a village or coordinates "
    "is already resolved -- never ask for one.\n\n"
    "IMPORTANT -- there are exactly two things this system ever needs to "
    "answer a flood question: (1) a location (village or coordinates), and "
    "(2) a nameable topic (even a broad one, e.g. \"flood outlook\", "
    "\"shelters\", \"government policy\", \"evacuation\"). Once BOTH are "
    "available -- directly in the current message, resolved via 'Location "
    "already provided', OR inherited from established conversation history "
    "-- the request is genuine_question, full stop. Never invent a THIRD "
    "axis to ask about: not which narrower sub-aspect (\"weather vs. "
    "forecast\"), not which geographic scope (\"this village or the "
    "broader district\"), not timeframe, not phrasing precision. This "
    "system answers holistically from whatever real evidence exists; it "
    "resolves those finer points in the answer itself, never by asking the "
    "user first. A follow-up in an established conversation ALWAYS applies "
    "to the same location already established -- never ask whether it "
    "means a different, broader, or otherwise unspecified location. "
    "Established history makes intent clearer, never less clear.\n\n"
    "Correctly genuine_question (do not ask anything further): \"What is "
    "the flood outlook for Saidu Sharif?\" (location + topic both named). "
    "\"What about shelters?\" or \"What about the government policy?\" as "
    "a follow-up after a village was already discussed (topic named, "
    "location inherited from history -- do not ask whether they mean this "
    "village, a different one, or the whole district).\n\n"
    "Correctly needs_clarification (genuinely nothing to go on): \"Is it "
    "safe?\" or \"Tell me about the flooding\" with no named location, no "
    "named topic beyond flooding in general, and no history to inherit "
    "either from.\n\n"
    "genuine_question -- a specific, answerable question this assistant is "
    "positioned to answer from real evidence or retrieval. Leave "
    "response_text as an empty string; a grounded answer is generated "
    "separately from real evidence, not by you.\n\n"
    "When uncertain, prefer genuine_question: never guess "
    "needs_clarification for a message that already contains enough "
    "specific detail to attempt a real answer, and never fabricate "
    "capability claims beyond what is listed below.\n\n"
    "Return only JSON that validates against the supplied schema."
)


class IntentPromptBuilder:
    """Build deterministic, mode-aware classification prompts."""

    def build(
        self,
        request_text: str,
        *,
        mode: ConversationMode,
        history: Sequence[ConversationTurnLike] = (),
        has_location: bool = False,
    ) -> tuple[str, str]:
        """Return system and user prompts for one turn's intent classification.

        ``has_location`` reflects the SAME structural fact
        ``ConversationOrchestrator`` already checks before running the flood
        graph (a resolved village or coordinates on the current request) --
        it is not inferred from conversation text, since a prior turn's
        free-text summary is an unreliable proxy for whether a location is
        actually established. Only meaningful for ``FLOOD_AGENT``; Policy
        Advisor has no location concept, so the line is omitted there.
        """
        capabilities = (
            _FLOOD_AGENT_CAPABILITIES
            if mode is ConversationMode.FLOOD_AGENT
            else _POLICY_ADVISOR_CAPABILITIES
        )
        system_prompt = (
            f"{_SYSTEM_INSTRUCTIONS}\n\nThis assistant's real capabilities:\n"
            f"{capabilities}"
        )
        history_section = _history_section(history)
        location_section = (
            f"Location already provided: {'true' if has_location else 'false'}\n\n"
            if mode is ConversationMode.FLOOD_AGENT
            else ""
        )
        user_prompt = (
            f"{history_section}{location_section}Current message:\n{request_text}"
        )
        return system_prompt, user_prompt


def _history_section(history: Sequence[ConversationTurnLike]) -> str:
    """Render bounded prior-turn context so clarification isn't repeated."""
    if not history:
        return ""
    turns = [
        {
            "request_text": turn.request_text,
            "prior_response": turn.recommendation_summary,
        }
        for turn in history
    ]
    return "Conversation history:\n" + json.dumps(
        turns, sort_keys=True, separators=(",", ":")
    ) + "\n\n"


class OpenAIIntentClassifier:
    """Adapt an injected async OpenAI client to ``IntentClassifierProtocol``.

    Deliberately simpler than ``OpenAIDecisionProvider``: no retry loop, no
    circuit breaker, no health tracking. Every failure mode here has a safe,
    cheap fallback one layer up (the orchestrator treats any
    ``IntentClassificationError`` as "run the existing default pipeline"),
    so a single bounded-timeout attempt is enough -- unlike the decision
    agent, there is no correctness property this class alone must uphold.
    """

    def __init__(
        self,
        *,
        client: object,
        prompt_builder: IntentPromptBuilder,
        model: str,
        timeout_seconds: float = 12.0,
    ) -> None:
        """Initialize explicit client, prompt, model, and timeout dependencies."""
        self._client = client
        self._prompt_builder = prompt_builder
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def classify(
        self,
        request_text: str,
        *,
        mode: ConversationMode,
        history: Sequence[ConversationTurnLike] = (),
        has_location: bool = False,
    ) -> IntentClassification:
        """Return a structured classification, translating any failure uniformly."""
        system_prompt, user_prompt = self._prompt_builder.build(
            request_text, mode=mode, history=history, has_location=has_location
        )
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=(
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ),
                    temperature=0.0,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "intent_classification",
                            "strict": True,
                            "schema": _strict_schema(),
                        },
                    },
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as error:
            raise IntentClassificationError(
                "Intent classifier request timed out."
            ) from error
        except Exception as error:
            raise IntentClassificationError(
                "Intent classifier request failed."
            ) from error

        content = _completion_content(response)
        try:
            return IntentClassification.model_validate_json(content)
        except ValidationError as error:
            raise IntentClassificationError(
                "Intent classifier returned an invalid structured response."
            ) from error


def _completion_content(response: object) -> str:
    """Extract one non-empty structured response without leaking SDK details."""
    choices = getattr(response, "choices", None)
    if not choices:
        raise IntentClassificationError("Intent classifier returned no choices.")
    content = choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise IntentClassificationError("Intent classifier returned empty content.")
    return content


def _strict_schema() -> dict[str, object]:
    """Return the flat, non-nested strict-mode schema for ``IntentClassification``."""
    schema = IntentClassification.model_json_schema()
    schema["additionalProperties"] = False
    schema["required"] = list(schema["properties"])
    return schema
