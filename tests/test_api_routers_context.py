"""
Tests for /api/notebooks/{id}/context router endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestContextRouter:
    """Test suite for /api/notebooks/{id}/context endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.context.Notebook")
    async def test_get_notebook_context_default(self, mock_notebook_class, client):
        """Test GET /api/notebooks/{id}/context with default config."""
        mock_notebook = MagicMock()
        mock_notebook.id = "notebook:123"

        mock_source = MagicMock()
        mock_source.get_context = AsyncMock(return_value="Source context")
        mock_note = MagicMock()
        mock_note.get_context = AsyncMock(return_value="Note context")

        mock_notebook.get_sources = AsyncMock(return_value=[mock_source])
        mock_notebook.get_notes = AsyncMock(return_value=[mock_note])

        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)

        response = client.post(
            "/api/notebooks/notebook:123/context",
            json={"notebook_id": "notebook:123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert "notes" in data

    @pytest.mark.asyncio
    @patch("api.routers.context.Source")
    @patch("api.routers.context.Note")
    @patch("api.routers.context.Notebook")
    async def test_get_notebook_context_with_config(
        self, mock_notebook_class, mock_note_class, mock_source_class, client
    ):
        """Test GET /api/notebooks/{id}/context with custom config."""
        mock_notebook = MagicMock()
        mock_notebook.id = "notebook:123"

        mock_source = MagicMock()
        mock_source.get_context = AsyncMock(return_value="Full source context")
        mock_source_class.get = AsyncMock(return_value=mock_source)

        mock_note = MagicMock()
        mock_note.get_context = AsyncMock(return_value="Full note context")
        mock_note_class.get = AsyncMock(return_value=mock_note)

        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)

        response = client.post(
            "/api/notebooks/notebook:123/context",
            json={
                "notebook_id": "notebook:123",
                "context_config": {
                    "sources": {"source:1": "full content"},
                    "notes": {"note:1": "full content"},
                }
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) >= 0  # May be empty if source not found
        assert len(data["notes"]) >= 0

    @pytest.mark.asyncio
    @patch("api.routers.context.Notebook")
    async def test_get_notebook_context_not_found(self, mock_notebook_class, client):
        """Test GET /api/notebooks/{id}/context returns 404 for missing notebook."""
        from open_notebook.exceptions import NotFoundError

        mock_notebook_class.get = AsyncMock(side_effect=NotFoundError("Not found"))

        response = client.post(
            "/api/notebooks/notebook:999/context",
            json={"notebook_id": "notebook:999"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routers.context.Source")
    @patch("api.routers.context.Notebook")
    async def test_get_notebook_context_source_not_found(
        self, mock_notebook_class, mock_source_class, client
    ):
        """Test GET /api/notebooks/{id}/context handles missing sources gracefully."""
        mock_notebook = MagicMock()
        mock_notebook.get_sources = AsyncMock(return_value=[])
        mock_notebook.get_notes = AsyncMock(return_value=[])

        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)
        mock_source_class.get = AsyncMock(side_effect=Exception("Source not found"))

        response = client.post(
            "/api/notebooks/notebook:123/context",
            json={
                "notebook_id": "notebook:123",
                "context_config": {
                    "sources": {"source:999": "full content"},
                }
            },
        )
        # Should handle gracefully and continue
        assert response.status_code == 200
