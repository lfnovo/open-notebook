"""Tests for the generic external MCP retriever."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.ai.external_retriever import external_mcp_search


@pytest.mark.asyncio
async def test_disabled_when_url_unset():
    with patch.dict(os.environ, {}, clear=True):
        # Ensure the variable is not set
        os.environ.pop("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", None)
        result = await external_mcp_search("hello")
        assert result == []


@pytest.mark.asyncio
async def test_successful_search():
    fake_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "relevant context here"}]
        },
    }

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = AsyncMock()
    mock_resp.json = AsyncMock(return_value=fake_response)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

    with patch.dict(os.environ, {"OPEN_NOTEBOOK_EXTERNAL_MCP_URL": "http://test:8766"}):
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await external_mcp_search("query", limit=3)
            assert len(result) == 1
            assert "relevant context" in result[0]["content"]
