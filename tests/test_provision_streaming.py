"""`provision_langchain_model(streaming=True)` must reach the model builder.

Esperanto's `to_langchain()` passes `streaming=False` explicitly unless the
model is built with `streaming=True`, and langchain-core then falls back to one
whole-message chunk for `astream()`. These tests pin the kwarg on both the
explicit-model and default-model paths, and its absence otherwise.
"""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.ai.provision import provision_langchain_model


class _FakeLanguageModel:
    """Stands in for esperanto's `LanguageModel` (only the type check matters)."""

    def to_langchain(self):
        return object()


async def _provision(model_id=None, **kwargs):
    with (
        patch("open_notebook.ai.provision.LanguageModel", _FakeLanguageModel),
        patch(
            "open_notebook.ai.provision.model_manager.get_default_model",
            new=AsyncMock(return_value=_FakeLanguageModel()),
        ) as get_default,
        patch(
            "open_notebook.ai.provision.model_manager.get_model",
            new=AsyncMock(return_value=_FakeLanguageModel()),
        ) as get_model,
    ):
        await provision_langchain_model("hello", model_id, "chat", **kwargs)
    return get_default, get_model


@pytest.mark.asyncio
async def test_streaming_flag_reaches_the_default_model():
    get_default, _ = await _provision(streaming=True)

    assert get_default.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_streaming_flag_reaches_an_explicit_model():
    _, get_model = await _provision("model:1", streaming=True)

    assert get_model.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_streaming_is_left_out_by_default():
    get_default, _ = await _provision()

    assert "streaming" not in get_default.await_args.kwargs
