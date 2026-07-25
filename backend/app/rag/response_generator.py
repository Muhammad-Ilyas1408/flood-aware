"""Official OpenAI response generator isolated behind a narrow contract."""

from typing import Protocol

from backend.app.rag.exceptions import AIRuntimeError
from backend.app.rag.protocols import ResponseGenerator


class _Completions(Protocol):
    def create(self, **kwargs: object) -> object: ...


class OpenAIResponseGenerator(ResponseGenerator):
    """Generate raw text using an injected or explicitly configured OpenAI client."""

    def __init__(
        self,
        client: object | None = None,
        api_key: str | None = None,
        model: str = "gpt-4.1-mini",
    ) -> None:
        if client is None:
            if not api_key:
                raise AIRuntimeError("An explicit OpenAI API key is required.")
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
        self._client = client
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate one non-streaming response without parsing or enrichment."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
            text = response.choices[0].message.content
        except Exception as error:
            raise AIRuntimeError(
                "Government knowledge response generation failed."
            ) from error
        if not isinstance(text, str) or not text.strip():
            raise AIRuntimeError("The response generator returned blank text.")
        return text
