"""Open Notebook defaults ESPERANTO_LLM_TIMEOUT to 180 s (#1434).

esperanto 2.28 enforces the timeout in to_langchain() on every provider, with
a 60 s default that cuts off long answers and slow local models.
"""

import pytest
from esperanto import AIFactory

from open_notebook.config import DEFAULT_LLM_TIMEOUT_SECONDS, ensure_llm_timeout_default


def test_default_applies_when_unset():
    env: dict[str, str] = {}
    ensure_llm_timeout_default(env)
    assert env["ESPERANTO_LLM_TIMEOUT"] == "180"
    assert DEFAULT_LLM_TIMEOUT_SECONDS == 180


@pytest.mark.parametrize("value", ["", "   "])
def test_default_applies_when_blank(value):
    env = {"ESPERANTO_LLM_TIMEOUT": value}
    ensure_llm_timeout_default(env)
    assert env["ESPERANTO_LLM_TIMEOUT"] == "180"


def test_explicit_value_wins():
    env = {"ESPERANTO_LLM_TIMEOUT": "90"}
    ensure_llm_timeout_default(env)
    assert env["ESPERANTO_LLM_TIMEOUT"] == "90"


@pytest.mark.parametrize(
    "env_value,expected",
    [(None, 180.0), ("90", 90.0)],
)
def test_langchain_model_carries_the_timeout(monkeypatch, env_value, expected):
    monkeypatch.delenv("ESPERANTO_LLM_TIMEOUT", raising=False)
    if env_value is not None:
        monkeypatch.setenv("ESPERANTO_LLM_TIMEOUT", env_value)
    import os

    ensure_llm_timeout_default(os.environ)

    model = AIFactory.create_language(
        "anthropic", "claude-sonnet-5", config={"api_key": "test"}
    ).to_langchain()

    assert float(model.default_request_timeout) == expected
