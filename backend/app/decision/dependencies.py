"""Explicit construction for the real OpenAI decision provider."""

from openai import AsyncOpenAI

from backend.app.core.application_exceptions import ApplicationConfigurationError
from backend.app.decision.agent import OpenAIDecisionProvider
from backend.app.decision.parser import DecisionParser
from backend.app.decision.prompt_builder import PromptBuilder
from backend.app.decision.settings import DecisionSettings


def build_openai_decision_provider() -> OpenAIDecisionProvider:
    """Build a configured async OpenAI decision provider for live evaluation.

    Raises:
        ApplicationConfigurationError: If ``OPENAI_API_KEY`` is unavailable.
    """
    settings = DecisionSettings()
    if not settings.openai_api_key:
        raise ApplicationConfigurationError(
            "OPENAI_API_KEY is required to build the OpenAI decision provider."
        )
    return OpenAIDecisionProvider(
        client=AsyncOpenAI(api_key=settings.openai_api_key),
        prompt_builder=PromptBuilder(),
        parser=DecisionParser(),
        model=settings.model,
    )
