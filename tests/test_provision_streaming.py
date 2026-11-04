"""`provision_langchain_model` only enables streaming on request.

Esperanto's `to_langchain()` always passes `streaming` to `ChatOpenAI`, and
langchain-core treats an explicit `streaming=False` as a hard opt-out:
`astream()` then falls back to `ainvoke()` and the whole answer arrives as one
chunk. The streaming endpoints must therefore opt in here; buffered callers
must stay on the default.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeLangChainModel:
    pass


class _FakeEsperantoModel:
    def to_langchain(self):
        return _FakeLangChainModel()


@pytest.fixture
def manager():
    fake = MagicMock()
    fake.get_model = AsyncMock(return_value=_FakeEsperantoModel())
    fake.get_default_model = AsyncMock(return_value=_FakeEsperantoModel())
    with (
        patch("open_notebook.ai.provision.model_manager", fake),
        patch("open_notebook.ai.provision.LanguageModel", _FakeEsperantoModel),
    ):
        yield fake


@pytest.mark.asyncio
async def test_default_provisioning_does_not_set_streaming(manager):
    from open_notebook.ai.provision import provision_langchain_model

    await provision_langchain_model("hi", "model:1", "chat", max_tokens=10)

    assert "streaming" not in manager.get_model.await_args.kwargs
    assert manager.get_model.await_args.kwargs["max_tokens"] == 10


@pytest.mark.asyncio
async def test_streaming_provisioning_opts_in(manager):
    from open_notebook.ai.provision import provision_langchain_model

    await provision_langchain_model("hi", "model:1", "chat", streaming=True)

    assert manager.get_model.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_streaming_flag_reaches_the_default_model_path(manager):
    from open_notebook.ai.provision import provision_langchain_model

    await provision_langchain_model("hi", None, "chat", streaming=True)

    manager.get_default_model.assert_awaited_once()
    assert manager.get_default_model.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_streaming_flag_reaches_the_large_context_path(manager):
    from open_notebook.ai.provision import provision_langchain_model

    with patch("open_notebook.ai.provision.token_count", return_value=200_000):
        await provision_langchain_model("hi", "model:1", "chat", streaming=True)

    assert manager.get_default_model.await_args.args[0] == "large_context"
    assert manager.get_default_model.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_non_language_model_is_rejected(manager):
    from open_notebook.ai.provision import provision_langchain_model
    from open_notebook.exceptions import ConfigurationError

    manager.get_model.return_value = object()

    with pytest.raises(ConfigurationError, match="not a LanguageModel"):
        await provision_langchain_model("hi", "model:1", "chat")
