"""Retry, then fall back, when a provider refuses a podcast outline/transcript call.

Anthropic can answer a long request with `stop_reason: "refusal"` and no
content (a classifier false positive, and intermittent). podcast-creator then
parsed the empty string as JSON and failed with a bare "Invalid json output:".

`install_refusal_guard()` wraps podcast-creator's private
`_SchemaFallbackModel.ainvoke` (there is no public hook). Per call it:

1. retries the same request `PODCAST_REFUSAL_RETRIES` more times (default 2);
2. then tries `PODCAST_REFUSAL_FALLBACK_MODEL` (a model name on the same
   provider and credentials), if set;
3. otherwise raises `ModelRefusalError`, a ValueError so the library's own
   retry decorator treats it as permanent instead of repeating it.
"""

import os
from typing import Any, Awaitable, Callable, Optional

from esperanto import AIFactory
from loguru import logger

DEFAULT_REFUSAL_RETRIES = 2


class ModelRefusalError(ValueError):
    """The provider refused the request on every attempt."""


def refusal_reason(message: Any) -> Optional[str]:
    """Return a short reason when the reply is a refusal, else None."""
    meta = getattr(message, "response_metadata", None) or {}
    if meta.get("stop_reason") == "refusal":  # Anthropic
        details = meta.get("stop_details") or {}
        return str(details.get("category") or "refusal")
    if meta.get("finish_reason") == "content_filter":  # OpenAI-compatible
        return "content_filter"
    return None


def _retries() -> int:
    try:
        return max(0, int(os.environ.get("PODCAST_REFUSAL_RETRIES", "")))
    except ValueError:
        return DEFAULT_REFUSAL_RETRIES


def guard_ainvoke(
    original: Callable[[Any, str], Awaitable[Any]],
) -> Callable[[Any, str], Awaitable[Any]]:
    async def ainvoke(self: Any, prompt_text: str) -> Any:
        attempts = _retries() + 1
        reason: Optional[str] = None
        for attempt in range(1, attempts + 1):
            result = await original(self, prompt_text)
            reason = refusal_reason(result)
            if reason is None:
                return result
            logger.warning(
                f"{self.key} refused the request ({reason}), "
                f"attempt {attempt}/{attempts}"
            )

        fallback = os.environ.get("PODCAST_REFUSAL_FALLBACK_MODEL", "").strip()
        if fallback and fallback != self.model_name:
            logger.warning(f"Falling back to {self.provider}/{fallback}")
            model = AIFactory.create_language(
                self.provider, fallback, config=self._config
            ).to_langchain()
            result = await model.ainvoke(prompt_text)
            reason = refusal_reason(result)
            if reason is None:
                return result
            logger.warning(f"{self.provider}/{fallback} refused too ({reason})")

        raise ModelRefusalError(
            f"{self.key} refused the request ({reason}) on every attempt"
        )

    ainvoke._refusal_guarded = True  # type: ignore[attr-defined]
    return ainvoke


def install_refusal_guard() -> None:
    """Patch podcast-creator once; safe to call repeatedly."""
    import podcast_creator.nodes as nodes

    model_cls = nodes._SchemaFallbackModel
    if not getattr(model_cls.ainvoke, "_refusal_guarded", False):
        model_cls.ainvoke = guard_ainvoke(model_cls.ainvoke)  # type: ignore[method-assign]
