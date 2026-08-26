"""Deterministic detection and reply generation for casual, non-flood turns.

Shared by every conversation mode so neither Flood-Aware Agent nor Policy
Advisor has to special-case greetings, thanks, or farewells on its own: both
reach this module through the one ``ConversationOrchestrator`` choke point.
This is a heuristic first pass (exact/short-phrase matching), not a semantic
classifier -- it is deliberately conservative, matching only inputs that are
almost entirely a greeting/thanks/farewell rather than a flood or policy
question that happens to open with "hi".
"""

import re

from backend.app.conversation.models import ConversationMode

_SMALL_TALK_PHRASES = frozenset(
    {
        "hi",
        "hii",
        "hiya",
        "hello",
        "hey",
        "yo",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how's it going",
        "hows it going",
        "what's up",
        "whats up",
        "who are you",
        "what can you do",
        "what do you do",
        "thanks",
        "thank you",
        "thanks a lot",
        "thank you very much",
        "ok",
        "okay",
        "cool",
        "great",
        "bye",
        "goodbye",
        "see you",
        "see ya",
    }
)

_TRAILING_PUNCTUATION = re.compile(r"[!.?,\s]+$")


def is_small_talk(request_text: str) -> bool:
    """Return whether ``request_text`` is casual conversation, not a real question.

    Only exact (case-insensitive, punctuation-trimmed) matches against a fixed
    phrase set qualify -- anything with additional content (e.g. "hi, is
    Mingora at risk today?") is left to the full pipeline, since a false
    negative here just means an ordinary turn, while a false positive would
    silently drop a real flood or policy question.
    """
    normalized = _TRAILING_PUNCTUATION.sub("", request_text.strip().lower())
    return normalized in _SMALL_TALK_PHRASES


_FLOOD_AGENT_REPLY = (
    "Hi! I'm the Flood-Aware assistant. Ask me about flood risk for a "
    "specific place -- share coordinates or a village name and I'll pull "
    "together the latest forecast, GIS, and shelter evidence for you."
)
_POLICY_ADVISOR_REPLY = (
    "Hi! I'm Policy Advisor. Ask me about government flood policy, "
    "disaster-management plans, or official evacuation guidance, and I'll "
    "answer from the real PDMA/NDMP documents."
)


def small_talk_reply(mode: ConversationMode) -> str:
    """Return one mode-appropriate canned reply for a detected small-talk turn."""
    if mode is ConversationMode.POLICY_ADVISOR:
        return _POLICY_ADVISOR_REPLY
    return _FLOOD_AGENT_REPLY
