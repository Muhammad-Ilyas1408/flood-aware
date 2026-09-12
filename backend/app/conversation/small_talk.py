"""Deterministic detection and reply generation for casual, non-flood turns.

Shared by every conversation mode so neither Flood-Aware Agent nor Policy
Advisor has to special-case greetings, thanks, or farewells on its own: both
reach this module through the one ``ConversationOrchestrator`` choke point.
This is a heuristic first pass (exact/short-phrase matching), not a semantic
classifier -- it is deliberately conservative, matching only inputs that are
almost entirely a greeting/thanks/farewell rather than a flood or policy
question that happens to open with "hi".
"""

import random
import re
from enum import Enum

from backend.app.conversation.models import ConversationMode

_TRAILING_PUNCTUATION = re.compile(r"[!.?,\s]+$")


def _normalize(request_text: str) -> str:
    return _TRAILING_PUNCTUATION.sub("", request_text.strip().lower())


class _Category(Enum):
    """Group small-talk phrases so the canned reply can match their intent."""

    GREETING = "greeting"
    STATUS_CHECK = "status_check"
    IDENTITY = "identity"
    THANKS = "thanks"
    ACKNOWLEDGMENT = "acknowledgment"
    FAREWELL = "farewell"


_PHRASE_CATEGORY: dict[str, _Category] = {
    "hi": _Category.GREETING,
    "hii": _Category.GREETING,
    "hiya": _Category.GREETING,
    "hello": _Category.GREETING,
    "hey": _Category.GREETING,
    "yo": _Category.GREETING,
    "good morning": _Category.GREETING,
    "good afternoon": _Category.GREETING,
    "good evening": _Category.GREETING,
    "how are you": _Category.STATUS_CHECK,
    "how's it going": _Category.STATUS_CHECK,
    "hows it going": _Category.STATUS_CHECK,
    "what's up": _Category.STATUS_CHECK,
    "whats up": _Category.STATUS_CHECK,
    "who are you": _Category.IDENTITY,
    "what can you do": _Category.IDENTITY,
    "what do you do": _Category.IDENTITY,
    "thanks": _Category.THANKS,
    "thank you": _Category.THANKS,
    "thanks a lot": _Category.THANKS,
    "thank you very much": _Category.THANKS,
    "ok": _Category.ACKNOWLEDGMENT,
    "okay": _Category.ACKNOWLEDGMENT,
    "cool": _Category.ACKNOWLEDGMENT,
    "great": _Category.ACKNOWLEDGMENT,
    "bye": _Category.FAREWELL,
    "goodbye": _Category.FAREWELL,
    "see you": _Category.FAREWELL,
    "see ya": _Category.FAREWELL,
}


def is_small_talk(request_text: str) -> bool:
    """Return whether ``request_text`` is casual conversation, not a real question.

    Only exact (case-insensitive, punctuation-trimmed) matches against a fixed
    phrase set qualify -- anything with additional content (e.g. "hi, is
    Mingora at risk today?") is left to the full pipeline, since a false
    negative here just means an ordinary turn, while a false positive would
    silently drop a real flood or policy question.
    """
    return _normalize(request_text) in _PHRASE_CATEGORY


_FLOOD_AGENT_REPLIES: dict[_Category, tuple[str, ...]] = {
    _Category.GREETING: (
        "Hi! I'm Flood Guide. Share a village name or "
        "coordinates and I'll pull together the latest forecast, GIS, and "
        "shelter evidence for you.",
        "Hey there! I'm here to help with flood risk for Swat district -- "
        "pick a village above and ask away.",
    ),
    _Category.STATUS_CHECK: (
        "Doing well, thanks for asking! Ready to check flood risk whenever "
        "you are -- just pick a village and ask.",
        "All good on my end. Select a village above and I'll pull the "
        "latest evidence for you.",
    ),
    _Category.IDENTITY: (
        "I'm Flood Guide. Ask me about flood risk for a "
        "specific place -- share coordinates or a village name and I'll "
        "pull together the latest forecast, GIS, and shelter evidence for "
        "you.",
        "I assess flood risk for villages in Swat district using live "
        "weather, river-forecast, GIS, and shelter data. Pick a village "
        "above to get started.",
    ),
    _Category.THANKS: (
        "You're welcome! Let me know if you'd like another risk check.",
        "Happy to help -- ask anytime.",
    ),
    _Category.ACKNOWLEDGMENT: (
        "Sounds good. Let me know what you'd like to check next.",
        "Got it -- I'm here whenever you're ready.",
    ),
    _Category.FAREWELL: (
        "Take care! Come back anytime you need a flood risk check.",
        "Goodbye -- stay safe out there.",
    ),
}

_POLICY_ADVISOR_REPLIES: dict[_Category, tuple[str, ...]] = {
    _Category.GREETING: (
        "Hi! I'm Policy Advisor. Ask me about government flood policy, "
        "disaster-management plans, or official evacuation guidance.",
        "Hello! I answer questions from the real PDMA/NDMP documents -- "
        "what would you like to know?",
    ),
    _Category.STATUS_CHECK: (
        "Doing well! Ready to answer questions on flood policy and "
        "disaster-management plans whenever you are.",
        "All good -- ask me anything about PDMA or NDMP guidance.",
    ),
    _Category.IDENTITY: (
        "I'm Policy Advisor. Ask me about government flood policy, "
        "disaster-management plans, or official evacuation guidance, and "
        "I'll answer from the real PDMA/NDMP documents.",
        "I answer questions grounded in official PDMA and NDMP documents "
        "-- policy, evacuation procedures, disaster-management plans.",
    ),
    _Category.THANKS: (
        "You're welcome! Ask me anything else about flood policy or "
        "evacuation guidance.",
        "Glad to help -- feel free to ask another policy question.",
    ),
    _Category.ACKNOWLEDGMENT: (
        "Sounds good. Let me know what policy question you'd like "
        "answered.",
        "Got it -- ask away whenever you're ready.",
    ),
    _Category.FAREWELL: (
        "Goodbye! Come back anytime with policy questions.",
        "Take care -- happy to help again anytime.",
    ),
}

_REPLIES_BY_MODE: dict[ConversationMode, dict[_Category, tuple[str, ...]]] = {
    ConversationMode.FLOOD_AGENT: _FLOOD_AGENT_REPLIES,
    ConversationMode.POLICY_ADVISOR: _POLICY_ADVISOR_REPLIES,
}


def small_talk_reply(request_text: str, mode: ConversationMode) -> str:
    """Return one mode- and category-appropriate reply for a small-talk turn.

    ``request_text`` is assumed to already satisfy ``is_small_talk``; an
    unrecognized phrase falls back to the mode's greeting variants rather
    than raising, since this only runs after that check has already passed.
    """
    category = _PHRASE_CATEGORY.get(_normalize(request_text), _Category.GREETING)
    variants = _REPLIES_BY_MODE[mode][category]
    return random.choice(variants)
