"""
Tests for /api/insights router endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInsightsRouter:
    """Test suite for /api/insights endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.insights.SourceInsight")
    async def test_get_insight(self, mock_insight_class, client):
        """Test GET /api/insights/{id} returns insight."""
        mock_insight = MagicMock()
        mock_insight.id = "insight:123"
        mock_insight.insight_type = "summary"
        mock_insight.content = "Summary content"
        mock_insight.created = "2024-01-01T00:00:00"
        mock_insight.updated = "2024-01-01T00:00:00"
        mock_insight.get_source = AsyncMock()

        mock_source = MagicMock()
        mock_source.id = "source:456"
        mock_insight.get_source.return_value = mock_source

        mock_insight_class.get = AsyncMock(return_value=mock_insight)

        response = client.get("/api/insights/insight:123")
        assert response.status_code == 200
        data = response.json()
        assert data["insight_type"] == "summary"
        assert data["source_id"] == "source:456"

    @pytest.mark.asyncio
    @patch("api.routers.insights.SourceInsight")
    async def test_get_insight_not_found(self, mock_insight_class, client):
        """Test GET /api/insights/{id} returns 404 for missing insight."""
        from open_notebook.exceptions import NotFoundError

        mock_insight_class.get = AsyncMock(side_effect=NotFoundError("Not found"))

        response = client.get("/api/insights/insight:999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routers.insights.SourceInsight")
    async def test_delete_insight(self, mock_insight_class, client):
        """Test DELETE /api/insights/{id} deletes insight."""
        mock_insight = MagicMock()
        mock_insight.delete = AsyncMock(return_value=True)

        mock_insight_class.get = AsyncMock(return_value=mock_insight)

        response = client.delete("/api/insights/insight:123")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    @pytest.mark.asyncio
    @patch("api.routers.insights.SourceInsight")
    async def test_save_insight_as_note(self, mock_insight_class, client):
        """Test POST /api/insights/{id}/save-as-note converts insight to note."""
        mock_insight = MagicMock()
        mock_insight.id = "insight:123"

        mock_note = MagicMock()
        mock_note.id = "note:789"
        mock_note.title = "Summary from source"
        mock_note.content = "Summary content"
        mock_note.note_type = "ai"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"

        mock_insight.save_as_note = AsyncMock(return_value=mock_note)
        mock_insight_class.get = AsyncMock(return_value=mock_insight)

        response = client.post(
            "/api/insights/insight:123/save-as-note",
            json={"notebook_id": "notebook:1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Summary from source"

    @pytest.mark.asyncio
    @patch("api.routers.insights.SourceInsight")
    async def test_save_insight_as_note_no_notebook(self, mock_insight_class, client):
        """Test POST /api/insights/{id}/save-as-note without notebook_id."""
        mock_insight = MagicMock()
        mock_note = MagicMock()
        mock_note.id = "note:789"
        mock_note.title = "Note"
        mock_note.content = "Content"
        mock_note.note_type = "ai"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"

        mock_insight.save_as_note = AsyncMock(return_value=mock_note)
        mock_insight_class.get = AsyncMock(return_value=mock_insight)

        response = client.post(
            "/api/insights/insight:123/save-as-note",
            json={},
        )
        assert response.status_code == 200
