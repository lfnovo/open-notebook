"""The external MCP retriever is off by default and fail-open when on."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.ai.external_retriever import (
    external_mcp_search,
    rows_from_tool_result,
)
from open_notebook.graphs.ask import provide_answer


def _clear_mcp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPEN_NOTEBOOK_EXTERNAL_MCP_URL",
        "OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN",
        "OPEN_NOTEBOOK_EXTERNAL_MCP_SEARCH_TOOL",
        "OPEN_NOTEBOOK_EXTERNAL_MCP_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_disabled_when_url_unset(monkeypatch: pytest.MonkeyPatch):
    _clear_mcp_env(monkeypatch)
    assert await external_mcp_search("hello") == []


@pytest.mark.asyncio
async def test_blank_url_is_disabled(monkeypatch: pytest.MonkeyPatch):
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", "   ")
    assert await external_mcp_search("hello") == []


def test_structured_results_are_namespaced():
    result = SimpleNamespace(
        isError=False,
        structuredContent={
            "results": [
                {"id": "doc-1", "content": "alpha", "score": 0.8, "title": "A"},
                {"text": "beta"},
                {"content": "   "},
                "not-a-dict",
            ]
        },
        content=[],
    )
    rows = rows_from_tool_result(result)
    assert rows == [
        {
            "id": "external:doc-1",
            "content": "alpha",
            "similarity": 0.8,
            "title": "A",
        },
        {"id": "external:2", "content": "beta"},
    ]


def test_text_content_becomes_one_snippet():
    result = SimpleNamespace(
        isError=False,
        structuredContent=None,
        content=[
            SimpleNamespace(text="first"),
            SimpleNamespace(text="second"),
        ],
    )
    assert rows_from_tool_result(result) == [
        {"id": "external:1", "content": "first\n\nsecond"}
    ]


def test_tool_error_yields_no_rows():
    result = SimpleNamespace(isError=True, structuredContent=None, content=[])
    assert rows_from_tool_result(result) == []


@pytest.mark.asyncio
async def test_connector_failure_does_not_raise(monkeypatch: pytest.MonkeyPatch):
    _clear_mcp_env(monkeypatch)
    monkeypatch.setenv("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", "https://mcp.example.com/mcp")
    with patch(
        "open_notebook.ai.external_retriever._call_search_tool",
        new=AsyncMock(side_effect=ConnectionError("down")),
    ):
        assert await external_mcp_search("term") == []


@pytest.mark.asyncio
async def test_ask_keeps_going_on_external_snippets_alone():
    state = {
        "question": "q",
        "term": "rag",
        "instructions": "extract",
        "notebook_ids": [],
    }
    model = AsyncMock()
    model.ainvoke = AsyncMock(
        return_value=SimpleNamespace(content="from the connector")
    )
    with (
        patch(
            "open_notebook.graphs.ask.vector_search",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "open_notebook.graphs.ask.external_mcp_search",
            new=AsyncMock(return_value=[{"id": "external:1", "content": "outside"}]),
        ),
        patch(
            "open_notebook.graphs.ask.provision_langchain_model",
            new=AsyncMock(return_value=model),
        ),
    ):
        result = await provide_answer(state, {"configurable": {}})  # type: ignore[arg-type]
    assert result == {"answers": ["from the connector"]}
