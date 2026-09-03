from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import open_notebook.graphs.transformation as transformation


@pytest.fixture(autouse=True)
def clear_transform_max_tokens_cache():
    transformation.get_transform_max_tokens.cache_clear()
    yield
    transformation.get_transform_max_tokens.cache_clear()


def test_transform_max_tokens_defaults_when_env_is_unset(monkeypatch):
    monkeypatch.delenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, raising=False)

    assert transformation.get_transform_max_tokens() == 8192


def test_transform_max_tokens_reads_positive_override(monkeypatch):
    monkeypatch.setenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, "12000")

    assert transformation.get_transform_max_tokens() == 12000


def test_transform_max_tokens_caches_process_value(monkeypatch):
    monkeypatch.setenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, "12000")

    assert transformation.get_transform_max_tokens() == 12000

    monkeypatch.setenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, "16000")
    assert transformation.get_transform_max_tokens() == 12000

    transformation.get_transform_max_tokens.cache_clear()
    assert transformation.get_transform_max_tokens() == 16000


@pytest.mark.parametrize("value", ["not-a-number", "0", "-5", "  "])
def test_transform_max_tokens_invalid_values_fall_back_to_default(monkeypatch, value):
    monkeypatch.setenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, value)

    assert transformation.get_transform_max_tokens() == 8192


@pytest.mark.asyncio
async def test_run_transformation_passes_configured_max_tokens(monkeypatch):
    monkeypatch.setenv(transformation.TRANSFORM_MAX_TOKENS_ENV_VAR, "15000")
    transformation.get_transform_max_tokens.cache_clear()

    fake_chain = MagicMock()
    fake_chain.ainvoke = AsyncMock(
        return_value=MagicMock(content="complete insight text")
    )
    provision = AsyncMock(return_value=fake_chain)

    with patch.object(transformation, "provision_langchain_model", provision):
        result = await transformation.run_transformation(
            {
                "input_text": "source transcript",
                "transformation": MagicMock(
                    prompt="Summarize",
                    title="Summary",
                    model_id=None,
                ),
            },
            {"configurable": {}},
        )

    assert result["output"] == "complete insight text"
    assert provision.await_args.kwargs["max_tokens"] == 15000
