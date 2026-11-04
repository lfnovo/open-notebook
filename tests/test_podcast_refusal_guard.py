"""A provider refusal must be retried, fall back, then fail with a clear error.

Anthropic can answer an outline/transcript call with `stop_reason: "refusal"`
and no content (a classifier false positive on long source text). The library
then parsed the empty string as JSON and failed with a bare
"Invalid json output:". The refusal is intermittent, so a retry usually passes.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from commands.podcast_commands import explain_generation_failure
from open_notebook.podcasts import refusal_guard
from open_notebook.podcasts.refusal_guard import (
    ModelRefusalError,
    guard_ainvoke,
    install_refusal_guard,
    refusal_reason,
)

OK = AIMessage(content='{"ok": true}', response_metadata={"stop_reason": "end_turn"})
REFUSED = AIMessage(
    content=[],
    response_metadata={
        "stop_reason": "refusal",
        "stop_details": {
            "type": "refusal",
            "category": "reasoning_extraction",
            "explanation": "blocked as it seems to violate the terms",
        },
    },
)


class FakeModel:
    """Stands in for podcast_creator's _SchemaFallbackModel."""

    provider = "anthropic"
    model_name = "claude-sonnet-5-5"
    key = "anthropic/claude-sonnet-5-5"
    _config = {"max_tokens": 8192}

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def original(self, prompt_text):
        self.calls += 1
        return self.replies.pop(0)


def guarded(model):
    async def original(self, prompt_text):
        return await model.original(prompt_text)

    return guard_ainvoke(original)


@pytest.fixture(autouse=True)
def no_env(monkeypatch):
    monkeypatch.delenv("PODCAST_REFUSAL_RETRIES", raising=False)
    monkeypatch.delenv("PODCAST_REFUSAL_FALLBACK_MODEL", raising=False)


def test_refusal_reason_detects_anthropic_refusal():
    reason = refusal_reason(REFUSED)
    assert reason is not None
    assert "reasoning_extraction" in reason
    assert refusal_reason(OK) is None


def test_refusal_reason_detects_openai_content_filter():
    msg = AIMessage(content="", response_metadata={"finish_reason": "content_filter"})
    assert refusal_reason(msg) is not None


@pytest.mark.asyncio
async def test_normal_reply_is_returned_after_one_call():
    model = FakeModel([OK])
    assert await guarded(model)(model, "p") is OK
    assert model.calls == 1


@pytest.mark.asyncio
async def test_refusal_is_retried_then_succeeds():
    model = FakeModel([REFUSED, REFUSED, OK])
    assert await guarded(model)(model, "p") is OK
    assert model.calls == 3


@pytest.mark.asyncio
async def test_exhausted_retries_raise_clear_error():
    model = FakeModel([REFUSED, REFUSED, REFUSED])
    with pytest.raises(ModelRefusalError) as exc:
        await guarded(model)(model, "p")
    assert model.calls == 3
    assert "anthropic/claude-sonnet-5-5" in str(exc.value)
    assert "refused" in str(exc.value)
    assert isinstance(exc.value, ValueError)  # permanent: outer retry skips it


@pytest.mark.asyncio
async def test_retry_count_comes_from_env(monkeypatch):
    monkeypatch.setenv("PODCAST_REFUSAL_RETRIES", "0")
    model = FakeModel([REFUSED])
    with pytest.raises(ModelRefusalError):
        await guarded(model)(model, "p")
    assert model.calls == 1


@pytest.mark.asyncio
async def test_fallback_model_used_after_retries(monkeypatch):
    monkeypatch.setenv("PODCAST_REFUSAL_FALLBACK_MODEL", "claude-haiku-5-5")
    model = FakeModel([REFUSED, REFUSED, REFUSED])
    fallback = MagicMock()

    async def fb_invoke(prompt_text):
        return OK

    fallback.ainvoke = fb_invoke
    with patch.object(refusal_guard, "AIFactory") as factory:
        factory.create_language.return_value.to_langchain.return_value = fallback
        assert await guarded(model)(model, "p") is OK
    factory.create_language.assert_called_once_with(
        "anthropic", "claude-haiku-5-5", config=FakeModel._config
    )
    assert model.calls == 3


@pytest.mark.asyncio
async def test_fallback_also_refused_raises(monkeypatch):
    monkeypatch.setenv("PODCAST_REFUSAL_FALLBACK_MODEL", "claude-haiku-5-5")
    model = FakeModel([REFUSED, REFUSED, REFUSED])
    fallback = MagicMock()

    async def fb_invoke(prompt_text):
        return REFUSED

    fallback.ainvoke = fb_invoke
    with patch.object(refusal_guard, "AIFactory") as factory:
        factory.create_language.return_value.to_langchain.return_value = fallback
        with pytest.raises(ModelRefusalError):
            await guarded(model)(model, "p")


@pytest.mark.asyncio
async def test_fallback_same_as_primary_is_skipped(monkeypatch):
    monkeypatch.setenv("PODCAST_REFUSAL_FALLBACK_MODEL", "claude-sonnet-5-5")
    model = FakeModel([REFUSED, REFUSED, REFUSED])
    with patch.object(refusal_guard, "AIFactory") as factory:
        with pytest.raises(ModelRefusalError):
            await guarded(model)(model, "p")
    factory.create_language.assert_not_called()


def test_install_patches_library_class_once():
    """Fails loudly if a podcast-creator upgrade renames the private class."""
    import podcast_creator.nodes as nodes

    install_refusal_guard()
    patched = nodes._SchemaFallbackModel.ainvoke
    install_refusal_guard()
    assert nodes._SchemaFallbackModel.ainvoke is patched
    assert getattr(patched, "_refusal_guarded", False)


def test_refusal_gets_an_actionable_hint():
    hint = explain_generation_failure(
        "anthropic/claude-sonnet-5-5 refused the request (reasoning_extraction)"
    )
    assert hint is not None
    assert "PODCAST_REFUSAL_FALLBACK_MODEL" in hint


@pytest.mark.asyncio
async def test_real_library_class_retries_a_refusal():
    """End to end through podcast-creator's own _SchemaFallbackModel."""
    import podcast_creator.nodes as nodes

    install_refusal_guard()
    replies = [REFUSED, OK]

    class Inner:
        async def ainvoke(self, prompt_text):
            return replies.pop(0)

    model = object.__new__(nodes._SchemaFallbackModel)
    model.provider, model.model_name = "anthropic", "claude-sonnet-5-5"
    model.key = "anthropic/claude-sonnet-5-5"
    model.uses_default_schema, model.json_mode = True, False
    model._config = {}
    model._model = Inner()
    assert await model.ainvoke("p") is OK
    assert replies == []
