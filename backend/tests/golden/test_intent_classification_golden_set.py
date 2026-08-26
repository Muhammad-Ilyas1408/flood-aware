"""Golden-set evaluation of real-time intent classification. Costs real API calls.

Complements ``backend/tests/conversation/test_intent.py``'s mocked classifier
tests, which only prove the classifier's request/response wiring and failure
handling are correct -- they cannot prove that a real utterance gets the
right label, since that is real LLM judgment.

The negative cases (``TestGenuineQuestionsAreNeverMisclassified``) are
weighted more heavily than the positive capability/clarification cases,
deliberately: a genuine, specific flood or policy question wrongly
classified as a capability question or a request for clarification
silently produces a non-answer for a question the system could actually
have answered -- a strictly worse failure than the reverse (an ambiguous
message wrongly reaching the full pipeline, which just reproduces the
already-tolerated pre-existing behavior this feature exists to improve on).
Two of the negative cases are deliberately adversarial: phrased as an
imperative request ("what should I do...") that a weaker classifier could
mistake for a meta question about the assistant itself, rather than a
genuine question about the assistant's actual subject matter.
"""

import os

import pytest

from backend.app.conversation.dependencies import build_openai_intent_classifier
from backend.app.conversation.intent import IntentLabel
from backend.app.conversation.models import ConversationMode

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_GOLDEN_SET") != "1",
        reason="Golden-set tests call the real OpenAI API; set RUN_GOLDEN_SET=1 to run.",
    ),
]


@pytest.fixture(scope="module")
def classifier():
    """Build the real, unmocked OpenAI intent classifier used by Golden-set evaluation."""
    return build_openai_intent_classifier()


_CAPABILITY_QUESTIONS = (
    (ConversationMode.FLOOD_AGENT, "How can you help me?"),
    (ConversationMode.FLOOD_AGENT, "What can I ask you?"),
    (ConversationMode.FLOOD_AGENT, "How do I use this?"),
    (ConversationMode.POLICY_ADVISOR, "How can you help me?"),
    (ConversationMode.POLICY_ADVISOR, "What kind of questions can I ask you?"),
    (ConversationMode.POLICY_ADVISOR, "What is this assistant for?"),
)

_CLARIFICATION_QUESTIONS = (
    (ConversationMode.FLOOD_AGENT, "Is it safe?"),
    (ConversationMode.FLOOD_AGENT, "Tell me about the flooding."),
    (ConversationMode.POLICY_ADVISOR, "Tell me about policy."),
    (ConversationMode.POLICY_ADVISOR, "What should I know?"),
)

# The critical negative set: real, specific, answerable questions that must
# reach the existing grounded pipeline unchanged. Deliberately larger than
# the positive sets above -- see module docstring.
_GENUINE_FLOOD_QUESTIONS = (
    "What is the flood risk for Mingora right now?",
    "What shelters are available near Kabal?",
    "Should residents evacuate given the current forecast?",
    "How many people are exposed to flooding in this area?",
    "What is the current river discharge and how does it compare to the "
    "moderate-risk threshold?",
    # Adversarial: an imperative "what should I do" framing could be
    # mistaken for a meta question about the assistant's own capabilities
    # rather than a genuine question about actual flood risk.
    "What should I do about the flood risk in Mingora right now?",
    # Adversarial follow-up shape: short, contains no place name at all, and
    # only makes sense given an already-selected location -- the exact shape
    # of the real false-positive this file's has_location=True below exists
    # to catch (see the module docstring and the has_location fix history).
    "What about shelters?",
)

_GENUINE_POLICY_QUESTIONS = (
    "What does the NDMP require district authorities to do before monsoon season?",
    "What is the government's evacuation policy for flood-prone areas?",
    "What are the official guidelines for pre-positioning relief stock?",
    "What steps does the national disaster plan require before a flood warning "
    "is issued?",
    "Who is responsible for coordinating evacuation drills under PDMA guidance?",
    # Adversarial: same imperative framing risk as above, applied to policy.
    "What should local authorities do to prepare shelters under PDMA guidance?",
)


@pytest.mark.parametrize("mode,question", _CAPABILITY_QUESTIONS)
class TestCapabilityQuestionClassification:
    async def test_capability_question_is_recognized(
        self, classifier, mode, question
    ) -> None:
        """A real capability/meta question must classify as CAPABILITY_QUESTION."""
        result = await classifier.classify(question, mode=mode)

        assert result.label is IntentLabel.CAPABILITY_QUESTION, (
            f"{question!r} in {mode} must classify as CAPABILITY_QUESTION, got "
            f"{result.label} ({result.response_text!r})."
        )
        assert result.response_text.strip(), (
            "A capability-question classification must generate real response text."
        )

    async def test_capability_answer_is_grounded_in_real_capabilities(
        self, classifier, mode, question
    ) -> None:
        """The generated answer must name this product's real capabilities, not invent any."""
        result = await classifier.classify(question, mode=mode)
        text = result.response_text.lower()

        if mode is ConversationMode.FLOOD_AGENT:
            assert any(keyword in text for keyword in ("swat", "village", "flood")), (
                f"Flood-agent capability answer must reference real product scope: "
                f"{result.response_text!r}"
            )
        else:
            assert any(
                keyword in text for keyword in ("pdma", "ndmp", "polic", "guidance")
            ), (
                f"Policy-advisor capability answer must reference real product scope: "
                f"{result.response_text!r}"
            )


@pytest.mark.parametrize("mode,question", _CLARIFICATION_QUESTIONS)
class TestClarificationClassification:
    async def test_vague_question_needs_clarification(
        self, classifier, mode, question
    ) -> None:
        """A genuinely vague on-topic question must produce a real clarifying question."""
        result = await classifier.classify(question, mode=mode, has_location=False)

        assert result.label is IntentLabel.NEEDS_CLARIFICATION, (
            f"{question!r} in {mode} must classify as NEEDS_CLARIFICATION, got "
            f"{result.label} ({result.response_text!r})."
        )
        assert result.response_text.strip().endswith("?"), (
            f"A clarification response must actually ask a question, got "
            f"{result.response_text!r}"
        )


@pytest.mark.parametrize("question", _GENUINE_FLOOD_QUESTIONS)
class TestGenuineFloodQuestionsAreNeverMisclassified:
    async def test_genuine_flood_question_reaches_the_real_pipeline(
        self, classifier, question
    ) -> None:
        """A real, specific flood question must never be diverted to a non-answer.

        ``has_location=True`` reflects these questions' realistic production
        context: a flood-agent question only ever reaches classification with
        a village or coordinates already resolved on the request (enforced
        structurally by ``MissingLocationError`` before a genuine question
        would otherwise run), so evaluating the classifier without that
        signal -- as this file originally did -- tests a scenario that never
        actually occurs and produces exactly the false-positive failures
        this fix addresses.
        """
        result = await classifier.classify(
            question, mode=ConversationMode.FLOOD_AGENT, has_location=True
        )

        assert result.label is IntentLabel.GENUINE_QUESTION, (
            f"{question!r} is a genuine, specific flood question and must reach "
            f"the full grounded pipeline unchanged; classifier instead returned "
            f"{result.label} ({result.response_text!r})."
        )


@pytest.mark.parametrize("question", _GENUINE_POLICY_QUESTIONS)
class TestGenuinePolicyQuestionsAreNeverMisclassified:
    async def test_genuine_policy_question_reaches_the_real_pipeline(
        self, classifier, question
    ) -> None:
        """A real, specific policy question must never be diverted to a non-answer."""
        result = await classifier.classify(
            question, mode=ConversationMode.POLICY_ADVISOR
        )

        assert result.label is IntentLabel.GENUINE_QUESTION, (
            f"{question!r} is a genuine, specific policy question and must reach "
            f"real RAG retrieval unchanged; classifier instead returned "
            f"{result.label} ({result.response_text!r})."
        )
