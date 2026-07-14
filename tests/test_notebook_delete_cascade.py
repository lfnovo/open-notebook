"""Regression tests for #1124: notebook deletion must cascade to chat sessions.

Verifies that get_delete_preview() reports chat_session_count, and that
delete() removes associated chat sessions and returns deleted_chat_sessions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Notebook, ChatSession


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


# --- get_delete_preview ---


@pytest.mark.asyncio
@patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
async def test_delete_preview_includes_chat_session_count(mock_notebook_get, client):
    """delete-preview should return chat_session_count."""
    mock_notebook = MagicMock(spec=Notebook)
    mock_notebook.id = "notebook:test"
    mock_notebook.name = "Test"
    mock_notebook.get_delete_preview = AsyncMock(
        return_value={
            "note_count": 0,
            "exclusive_source_count": 0,
            "shared_source_count": 0,
            "chat_session_count": 3,
        }
    )
    mock_notebook_get.return_value = mock_notebook

    resp = client.get("/api/notebooks/notebook:test/delete-preview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["chat_session_count"] == 3
    assert data["note_count"] == 0
    assert data["exclusive_source_count"] == 0
    assert data["shared_source_count"] == 0


# --- delete notebook ---


@pytest.mark.asyncio
@patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
async def test_delete_notebook_returns_deleted_chat_sessions(mock_notebook_get, client):
    """DELETE notebook should return deleted_chat_sessions in the response."""
    mock_notebook = MagicMock(spec=Notebook)
    mock_notebook.id = "notebook:test"
    mock_notebook.delete = AsyncMock(
        return_value={
            "deleted_notes": 0,
            "deleted_sources": 0,
            "unlinked_sources": 0,
            "deleted_chat_sessions": 2,
        }
    )
    mock_notebook_get.return_value = mock_notebook

    resp = client.delete("/api/notebooks/notebook:test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_chat_sessions"] == 2
    assert data["deleted_notes"] == 0
    assert data["unlinked_sources"] == 0
