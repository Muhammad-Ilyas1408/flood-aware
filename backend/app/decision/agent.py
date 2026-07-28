"""OpenAI-specific provider adapter for structured Flood-Aware decisions."""

from collections.abc import Awaitable, Sequence
import asyncio
from copy import deepcopy
import logging
from random import random
from typing import Callable, Protocol

from backend.app.core.logger import get_logger
from backend.app.decision.exceptions import (
    DecisionCircuitOpenError,
    DecisionError,
    DecisionGenerationError,
    DecisionGroundingError,
    DecisionParsingError,
    DecisionProviderTimeoutError,
    DecisionProviderUnavailableError,
    DecisionRateLimitedError,
    DecisionUnknownProviderError,
    LLMOutputValidationError,
)
from backend.app.decision.models import Decision
from backend.app.decision.parser import DecisionParser
from backend.app.decision.prompt_builder import PromptBuilder
from backend.app.decision.protocols import ConversationTurnLike
from backend.app.decision.resilience import (
    DecisionCircuitBreaker,
    DecisionExecutionMetadata,
    DecisionRuntimeConfig,
)
from backend.app.graph.state import EvidenceBundle
from backend.app.observability.context import ExecutionContext
from backend.app.observability.health import (
    DecisionProviderHealth,
    DecisionProviderHealthTracker,
)
from backend.app.observability.logging import log_event
from backend.app.observability.metrics import (
    DecisionMetricsCollector,
    LoggingDecisionMetricsCollector,
)
from backend.app.observability.timing import OperationTimer

_LOGGER = get_logger(__name__)


class _MessageProtocol(Protocol):
    """Represent the minimal structured message content used by this adapter."""

    content: str | None


class _ChoiceProtocol(Protocol):
    """Represent the minimal choice shape returned by OpenAI chat completions."""

    message: _MessageProtocol


class _UsageProtocol(Protocol):
    """Represent optional token usage metadata returned by a provider."""

    total_tokens: int | None


class _CompletionProtocol(Protocol):
    """Represent the minimal OpenAI completion response used by this adapter."""

    choices: Sequence[_ChoiceProtocol]
    usage: _UsageProtocol | None


class _CompletionsProtocol(Protocol):
    """Represent OpenAI's injected asynchronous chat-completions boundary."""

    async def create(self, **kwargs: object) -> _CompletionProtocol:
        """Create one structured chat completion."""


class _ChatProtocol(Protocol):
    """Represent the chat namespace of an injected OpenAI client."""

    completions: _CompletionsProtocol


class OpenAIClientProtocol(Protocol):
    """Narrow injected contract used by the OpenAI decision adapter."""

    chat: _ChatProtocol


class OpenAIDecisionProvider:
    """Adapt an injected OpenAI client to the provider-independent decision contract.

    This class owns only OpenAI request/response orchestration. Prompt construction
    remains in :class:`PromptBuilder`, and JSON validation remains in
    :class:`DecisionParser`. The client is constructor-injected; this module never
    creates or globally retains an SDK client.
    """

    def __init__(
        self,
        *,
        client: OpenAIClientProtocol,
        prompt_builder: PromptBuilder,
        parser: DecisionParser,
        model: str,
        runtime_config: DecisionRuntimeConfig | None = None,
        circuit_breaker: DecisionCircuitBreaker | None = None,
        metrics: DecisionMetricsCollector | None = None,
        health_tracker: DecisionProviderHealthTracker | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        random_source: Callable[[], float] = random,
    ) -> None:
        """Initialize explicit provider, prompt, parser, and model dependencies."""
        self._client = client
        self._prompt_builder = prompt_builder
        self._parser = parser
        self._model = model
        self._runtime_config = runtime_config or DecisionRuntimeConfig()
        self._circuit_breaker = circuit_breaker or DecisionCircuitBreaker(
            self._runtime_config
        )
        self._metrics = metrics or LoggingDecisionMetricsCollector()
        self._health_tracker = health_tracker or DecisionProviderHealthTracker()
        self._sleep = sleep or asyncio.sleep
        self._random_source = random_source

    async def decide(
        self,
        evidence: EvidenceBundle,
        *,
        execution_context: ExecutionContext | None = None,
        history: Sequence[ConversationTurnLike] = (),
    ) -> Decision:
        """Generate and parse one schema-constrained decision from evidence only."""
        system_prompt, user_prompt = self._prompt_builder.build(
            evidence,
            history=history,
        )
        context = execution_context or ExecutionContext.uncorrelated()
        timer = OperationTimer.start()
        log_event(
            _LOGGER,
            logging.INFO,
            "decision_provider_request_started",
            context,
            provider="openai",
            model=self._model,
        )
        if not await self._circuit_breaker.allow_request():
            failure = DecisionCircuitOpenError("Decision provider circuit is open.")
            self._log_failure(
                timer,
                context,
                DecisionExecutionMetadata(
                    attempt_count=0,
                    retry_count=0,
                    timeout_occurred=False,
                ),
                failure,
            )
            raise failure

        attempts = 0
        timeout_occurred = False
        correction_messages: tuple[dict[str, str], ...] = ()
        while True:
            attempts += 1
            try:
                response = await asyncio.wait_for(
                    self._create_completion(
                        system_prompt, user_prompt, correction_messages
                    ),
                    timeout=self._runtime_config.timeout_seconds,
                )
                parser_timer = OperationTimer.start()
                response_content = _completion_content(response)
                decision = self._parser.parse(response_content, evidence)
                log_event(
                    _LOGGER,
                    logging.INFO,
                    "decision_parser_finished",
                    context,
                    provider="openai",
                    model=self._model,
                    duration_ms=parser_timer.elapsed_ms(),
                )
            except asyncio.TimeoutError as error:
                timeout_occurred = True
                failure: DecisionGenerationError = DecisionProviderTimeoutError(
                    "Decision provider request timed out."
                )
                failure.__cause__ = error
            except DecisionGroundingError as error:
                failure = error
                if error.invalid_references:
                    correction_messages = (
                        *correction_messages,
                        {"role": "assistant", "content": response_content},
                        {
                            "role": "user",
                            "content": _grounding_correction_message(
                                error.invalid_references
                            ),
                        },
                    )
            except (DecisionParsingError, LLMOutputValidationError) as failure:
                self._log_failure(
                    timer,
                    context,
                    DecisionExecutionMetadata(
                        attempt_count=attempts,
                        retry_count=attempts - 1,
                        timeout_occurred=timeout_occurred,
                    ),
                    failure,
                )
                raise
            except Exception as error:
                failure = _translate_provider_failure(error)
                failure.__cause__ = error
            else:
                await self._circuit_breaker.record_success()
                self._health_tracker.record_success()
                self._metrics.record_provider_latency(
                    context, model=self._model, duration_ms=timer.elapsed_ms()
                )
                self._metrics.record_retry(context, retry_count=attempts - 1)
                self._metrics.record_success(context, model=self._model)
                if timeout_occurred:
                    self._metrics.record_timeout(context)
                token_count = _total_tokens(response)
                if token_count is not None:
                    self._metrics.record_tokens(context, token_count=token_count)
                self._log_completion(
                    timer,
                    context,
                    DecisionExecutionMetadata(
                        attempt_count=attempts,
                        retry_count=attempts - 1,
                        timeout_occurred=timeout_occurred,
                    ),
                    token_count,
                )
                return decision

            if (
                not _is_transient(failure)
                or attempts > self._runtime_config.retry_count
            ):
                if _is_transient(failure):
                    await self._circuit_breaker.record_failure()
                self._health_tracker.record_failure()
                self._metrics.record_failure(
                    context, failure_type=type(failure).__name__
                )
                self._metrics.record_retry(context, retry_count=attempts - 1)
                if timeout_occurred:
                    self._metrics.record_timeout(context)
                self._log_failure(
                    timer,
                    context,
                    DecisionExecutionMetadata(
                        attempt_count=attempts,
                        retry_count=attempts - 1,
                        timeout_occurred=timeout_occurred,
                    ),
                    failure,
                )
                raise failure
            await self._sleep(self._retry_delay(attempts))

    async def _create_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        correction_messages: Sequence[dict[str, str]] = (),
    ) -> _CompletionProtocol:
        """Create one provider completion, optionally continuing a grounding-correction turn."""
        return await self._client.chat.completions.create(
            model=self._model,
            messages=(
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                *correction_messages,
            ),
            temperature=0.0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "flood_aware_decision",
                    "strict": True,
                    "schema": _to_strict_openai_schema(Decision.model_json_schema()),
                },
            },
        )

    def _retry_delay(self, attempt: int) -> float:
        """Return bounded exponential backoff with injected bounded jitter."""
        delay = min(
            self._runtime_config.base_backoff_seconds * (2 ** (attempt - 1)),
            self._runtime_config.max_backoff_seconds,
        )
        return delay + self._runtime_config.jitter_seconds * self._random_source()

    def _log_completion(
        self,
        timer: OperationTimer,
        context: ExecutionContext,
        metadata: DecisionExecutionMetadata,
        token_count: int | None,
    ) -> None:
        """Log safe completion metadata without prompts, evidence, or responses."""
        log_event(
            _LOGGER,
            logging.INFO,
            "decision_provider_request_finished",
            context,
            provider="openai",
            model=self._model,
            duration_ms=timer.elapsed_ms(),
            retry_count=metadata.retry_count,
            attempt_count=metadata.attempt_count,
            timeout=metadata.timeout_occurred,
            fallback=metadata.fallback_used,
            token_count=token_count,
        )

    def _log_failure(
        self,
        timer: OperationTimer,
        context: ExecutionContext,
        metadata: DecisionExecutionMetadata,
        failure: DecisionError,
    ) -> None:
        """Log safe provider failure metadata without exposing SDK exception data."""
        log_event(
            _LOGGER,
            logging.WARNING,
            "decision_provider_request_failed",
            context,
            provider="openai",
            model=self._model,
            duration_ms=timer.elapsed_ms(),
            retry_count=metadata.retry_count,
            attempt_count=metadata.attempt_count,
            timeout=metadata.timeout_occurred,
            fallback=metadata.fallback_used,
            failure_type=type(failure).__name__,
        )

    @property
    def health(self) -> DecisionProviderHealth:
        """Return a local immutable health snapshot without performing I/O."""
        return self._health_tracker.snapshot(self._circuit_breaker.state)


def _completion_content(response: _CompletionProtocol) -> str:
    """Extract one non-empty structured response without leaking SDK details."""
    if not response.choices:
        raise DecisionGenerationError("Decision provider returned no choices.")
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise DecisionGenerationError("Decision provider returned empty content.")
    return content


def _to_strict_openai_schema(schema: dict[str, object]) -> dict[str, object]:
    """Return a copied schema compatible with OpenAI strict structured output."""
    normalized = deepcopy(schema)

    def normalize(value: object) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                value.setdefault("additionalProperties", False)
                value["required"] = list(properties)
            for child in value.values():
                normalize(child)
        elif isinstance(value, list):
            for child in value:
                normalize(child)

    normalize(normalized)
    return normalized


def _total_tokens(response: _CompletionProtocol) -> int | None:
    """Return optional provider token usage for observability only."""
    usage = response.usage
    return usage.total_tokens if usage is not None else None


def _is_transient(error: DecisionGenerationError) -> bool:
    """Return whether a translated provider error may be retried safely."""
    return isinstance(
        error,
        (
            DecisionProviderTimeoutError,
            DecisionProviderUnavailableError,
            DecisionRateLimitedError,
            DecisionGroundingError,
        ),
    )


def _grounding_correction_message(invalid_references: tuple[str, ...]) -> str:
    """Name the exact invalid citations so the model corrects only those."""
    return (
        "Your previous JSON response used these citation strings, which are NOT "
        f"present in 'Allowed citation values': {list(invalid_references)}. Return "
        "a corrected JSON decision that replaces ONLY these invalid citations with "
        "exact matches from 'Allowed citation values', keeping every other "
        "citation, reason, and piece of reasoning unchanged. Return the complete "
        "corrected JSON object, matching the original schema."
    )


def _translate_provider_failure(error: Exception) -> DecisionGenerationError:
    """Classify provider transport failures without importing provider SDK types."""
    status_code = getattr(error, "status_code", None)
    if status_code == 429:
        return DecisionRateLimitedError("Decision provider rate limit exceeded.")
    if isinstance(status_code, int) and 500 <= status_code <= 599:
        return DecisionProviderUnavailableError("Decision provider is unavailable.")
    if isinstance(error, (ConnectionError, OSError)):
        return DecisionProviderUnavailableError("Decision provider is unavailable.")
    return DecisionUnknownProviderError("Decision generation failed.")


# TODO(post-MVP): Add Azure OpenAI, Anthropic, Gemini, and local-model adapters
# without changing the DecisionAgentProtocol contract.
# TODO(post-MVP): Add provider cost, latency, and token reporting through a
# dedicated observability layer rather than this provider adapter.
# Compatibility alias retained for existing imports while callers adopt the
# provider-oriented implementation name.
OpenAIDecisionAgent = OpenAIDecisionProvider
