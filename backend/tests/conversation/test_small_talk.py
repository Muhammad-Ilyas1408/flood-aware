"""Unit tests for small-talk detection and category-aware canned replies."""

from backend.app.conversation.models import ConversationMode
from backend.app.conversation.small_talk import is_small_talk, small_talk_reply


def test_is_small_talk_matches_only_exact_phrases() -> None:
    """A real question that happens to open with a greeting is not small talk."""
    assert is_small_talk("hi")
    assert is_small_talk("  Hello!  ")
    assert not is_small_talk("hi, is Mingora at risk today?")
    assert not is_small_talk("What is the current flood condition here?")


def test_reply_pool_covers_every_matched_phrase_for_both_modes() -> None:
    """Every phrase ``is_small_talk`` accepts must resolve to a real reply in both modes."""
    phrases = (
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
    )
    for phrase in phrases:
        assert is_small_talk(phrase)
        for mode in ConversationMode:
            reply = small_talk_reply(phrase, mode)
            assert reply


def test_reply_varies_by_phrase_category_within_one_mode() -> None:
    """A greeting and a thanks in the same mode must not share the identical reply pool."""
    greeting_replies = {
        small_talk_reply("hi", ConversationMode.FLOOD_AGENT) for _ in range(30)
    }
    thanks_replies = {
        small_talk_reply("thanks", ConversationMode.FLOOD_AGENT) for _ in range(30)
    }
    assert greeting_replies.isdisjoint(thanks_replies)


def test_reply_has_more_than_one_variant_per_category() -> None:
    """Repeated greetings must not always return the identical string."""
    replies = {
        small_talk_reply("hi", ConversationMode.FLOOD_AGENT) for _ in range(50)
    }
    assert len(replies) > 1


def test_reply_differs_between_modes_for_the_same_phrase() -> None:
    """Flood-Agent and Policy Advisor must never share a reply pool."""
    flood_replies = {
        small_talk_reply("hi", ConversationMode.FLOOD_AGENT) for _ in range(30)
    }
    policy_replies = {
        small_talk_reply("hi", ConversationMode.POLICY_ADVISOR) for _ in range(30)
    }
    assert flood_replies.isdisjoint(policy_replies)
