"""Explicit construction for the real OpenAI intent classifier."""

from openai import AsyncOpenAI

from backend.app.conversation.intent import IntentPromptBuilder, OpenAIIntentClassifier
from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.decision.settings import DecisionSettings


def build_openai_intent_classifier() -> OpenAIIntentClassifier:
    """Build a configured OpenAI intent classifier for live conversation routing.

    Reuses ``DecisionSettings`` (API key and model) rather than a dedicated
    settings class: the classifier is a lightweight structured-output call
    sharing the same OpenAI credential and model as the decision provider,
    not a separately tunable production concern yet.

    Raises:
        ApplicationConfigurationError: If ``OPENAI_API_KEY`` is unavailable.
    """
    settings = DecisionSettings()
    if not settings.openai_api_key:
        raise ApplicationConfigurationError(
            "OPENAI_API_KEY is required to build the OpenAI intent classifier."
        )
    return OpenAIIntentClassifier(
        client=AsyncOpenAI(api_key=settings.openai_api_key),
        prompt_builder=IntentPromptBuilder(),
        model=settings.model,
    )
