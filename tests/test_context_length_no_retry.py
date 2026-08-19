"""Context-length rejections must fail immediately instead of being retried.

Regression coverage for #1231. A provider's context-length 400 is deterministic:
the same oversized payload is resent on every attempt, so retrying can never
succeed. Before the fix it surfaced as `ExternalServiceError` -- the same class
used for provider 5xx -- so the retry blocklist could not tell the two apart and
retried both, re-running the whole source pipeline for ~25 minutes.

Two properties are pinned here:

1. `classify_error()` maps a context-length message to `ContextLengthExceededError`
   (guards the rule and its ordering in `_CLASSIFICATION_RULES`).
2. The registered commands' retry configs stop on it after a single attempt,
   while a transient error still consumes the full retry budget (guards
   `stop_on`, and guards against over-correcting into "never retry anything").
"""

import pytest
from surreal_commands.core.registry import registry
from surreal_commands.core.retry import build_async_retry_instance

import commands  # noqa: F401  -- import registers the @command decorators
from open_notebook.exceptions import (
    ContextLengthExceededError,
    ExternalServiceError,
)
from open_notebook.utils.error_classifier import classify_error

# The message OpenRouter returned in #1231, as the OpenAI SDK surfaces it.
OPENROUTER_CONTEXT_LENGTH_400 = (
    "Error code: 400 - {'error': {'message': \"This endpoint's maximum context "
    "length is 262144 tokens. However, you requested about 403309 tokens "
    "(395117 of text input, 8192 in the output).\", 'code': 400}}"
)

# Commands whose retry config must treat context-length errors as permanent.
RETRY_COMMANDS = [
    "open_notebook.process_source",
    "open_notebook.run_transformation",
]


def _retry_config(command_id: str):
    """The live retry config the worker would actually use for this command."""
    item = registry.get_command_by_id(command_id)
    assert item is not None, f"{command_id} is not registered"
    assert item.retry_config is not None, f"{command_id} has no retry config"
    return item.retry_config


def _instant(config):
    """Same config, but without the real backoff, so tests don't sleep."""
    return config.model_copy(
        update={"wait_strategy": "fixed", "wait_time": 0, "wait_min": 0, "wait_max": 0}
    )


async def _count_attempts(config, exc: Exception) -> int:
    """Drive the real tenacity instance and report how many attempts it made."""
    attempts = 0
    retrying = build_async_retry_instance(_instant(config))
    with pytest.raises(type(exc)):
        async for attempt in retrying:
            with attempt:
                attempts += 1
                raise exc
    return attempts


class TestClassification:
    def test_openrouter_400_is_context_length_exceeded(self):
        exc_class, message = classify_error(Exception(OPENROUTER_CONTEXT_LENGTH_400))

        assert exc_class is ContextLengthExceededError
        assert message  # user-facing text, not empty

    def test_still_an_external_service_error(self):
        """Subclassing is load-bearing: it keeps the existing 502 handler."""
        assert issubclass(ContextLengthExceededError, ExternalServiceError)

    def test_provider_5xx_stays_retryable(self):
        """The regression guard -- 5xx must NOT be swept up as permanent."""
        exc_class, _ = classify_error(
            Exception("Error code: 503 - service unavailable, provider overloaded")
        )

        assert exc_class is ExternalServiceError
        assert not issubclass(exc_class, ContextLengthExceededError)


@pytest.mark.parametrize("command_id", RETRY_COMMANDS)
class TestRetryBehaviour:
    def test_stop_on_lists_context_length(self, command_id):
        assert ContextLengthExceededError in _retry_config(command_id).stop_on

    @pytest.mark.asyncio
    async def test_context_length_is_attempted_once(self, command_id):
        config = _retry_config(command_id)

        attempts = await _count_attempts(
            config, ContextLengthExceededError("Content too large")
        )

        assert attempts == 1, (
            f"{command_id} retried a deterministic context-length failure "
            f"{attempts} times; it must fail after the first attempt (#1231)"
        )

    @pytest.mark.asyncio
    async def test_transient_error_still_uses_full_budget(self, command_id):
        """Proves the fix narrows retries rather than disabling them."""
        config = _retry_config(command_id)

        attempts = await _count_attempts(
            config, RuntimeError("Failed to commit transaction due to a conflict")
        )

        assert attempts == config.max_attempts
