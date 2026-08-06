from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

import open_notebook.graphs.ask as ask


@pytest.fixture(autouse=True)
def clear_ask_max_tokens_cache():
    ask.get_ask_max_tokens.cache_clear()
    yield
    ask.get_ask_max_tokens.cache_clear()


def test_ask_max_tokens_defaults_when_env_is_unset(monkeypatch):
    monkeypatch.delenv(ask.ASK_MAX_TOKENS_ENV_VAR, raising=False)

    assert ask.get_ask_max_tokens() == 8192


def test_ask_max_tokens_reads_positive_override(monkeypatch):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "12000")

    assert ask.get_ask_max_tokens() == 12000


def test_ask_max_tokens_caches_process_value(monkeypatch):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "12000")

    assert ask.get_ask_max_tokens() == 12000

    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "16000")
    assert ask.get_ask_max_tokens() == 12000

    ask.get_ask_max_tokens.cache_clear()
    assert ask.get_ask_max_tokens() == 16000


@pytest.mark.parametrize("value", ["not-a-number", "0", "-5"])
def test_ask_max_tokens_invalid_values_fall_back_to_default(monkeypatch, value):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, value)

    assert ask.get_ask_max_tokens() == 8192


@pytest.mark.asyncio
async def test_strategy_uses_fixed_token_budget(monkeypatch):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "12000")
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value=SimpleNamespace(
                content='{"reasoning":"Need one search","searches":[]}'
            )
        )
    )
    provision = AsyncMock(return_value=model)
    monkeypatch.setattr(ask, "provision_langchain_model", provision)
    monkeypatch.setattr(
        ask.Prompter, "render", lambda self, **kwargs: "strategy prompt"
    )

    result = await ask.call_model_with_messages(
        cast(
            ask.ThreadState,
            {"question": "What is this?", "answers": [], "final_answer": ""},
        ),
        {"configurable": {"strategy_model": "strategy-model"}},
    )

    assert result == {
        "strategy": ask.Strategy(reasoning="Need one search", searches=[])
    }
    provision.assert_awaited_once_with(
        "strategy prompt",
        "strategy-model",
        "tools",
        max_tokens=2000,
        structured={"type": "json"},
    )
    model.ainvoke.assert_awaited_once_with("strategy prompt")


@pytest.mark.asyncio
async def test_provide_answer_uses_configured_token_budget(monkeypatch):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "12000")
    vector_search = AsyncMock(return_value=[{"id": "source:1"}])
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value=SimpleNamespace(content="<think>internal</think>Answer")
        )
    )
    provision = AsyncMock(return_value=model)
    monkeypatch.setattr(ask, "vector_search", vector_search)
    monkeypatch.setattr(ask, "provision_langchain_model", provision)
    monkeypatch.setattr(ask.Prompter, "render", lambda self, **kwargs: "answer prompt")

    result = await ask.provide_answer(
        cast(
            ask.SubGraphState,
            {
                "question": "What is this?",
                "term": "this",
                "instructions": "Explain it",
            },
        ),
        {"configurable": {"answer_model": "answer-model"}},
    )

    assert result == {"answers": ["Answer"]}
    vector_search.assert_awaited_once_with("this", 10, True, True)
    provision.assert_awaited_once_with(
        "answer prompt",
        "answer-model",
        "tools",
        max_tokens=12000,
    )
    model.ainvoke.assert_awaited_once_with("answer prompt")


@pytest.mark.asyncio
async def test_write_final_answer_uses_configured_token_budget(monkeypatch):
    monkeypatch.setenv(ask.ASK_MAX_TOKENS_ENV_VAR, "12000")
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value=SimpleNamespace(content="<think>internal</think>Final answer")
        )
    )
    provision = AsyncMock(return_value=model)
    monkeypatch.setattr(ask, "provision_langchain_model", provision)
    monkeypatch.setattr(ask.Prompter, "render", lambda self, **kwargs: "final prompt")

    result = await ask.write_final_answer(
        {
            "question": "What is this?",
            "strategy": ask.Strategy(reasoning="", searches=[]),
            "answers": ["Answer"],
            "final_answer": "",
        },
        {"configurable": {"final_answer_model": "final-model"}},
    )

    assert result == {"final_answer": "Final answer"}
    provision.assert_awaited_once_with(
        "final prompt",
        "final-model",
        "tools",
        max_tokens=12000,
    )
    model.ainvoke.assert_awaited_once_with("final prompt")
