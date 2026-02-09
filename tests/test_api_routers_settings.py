"""
Tests for /api/settings router endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSettingsRouter:
    """Test suite for /api/settings endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.settings.ContentSettings")
    async def test_get_settings(self, mock_content_settings, client):
        """Test GET /api/settings returns current settings."""
        mock_settings = MagicMock()
        mock_settings.default_content_processing_engine_doc = "auto"
        mock_settings.default_content_processing_engine_url = "auto"
        mock_settings.default_embedding_option = "ask"
        mock_settings.auto_delete_files = "yes"
        mock_settings.youtube_preferred_languages = ["en"]

        mock_content_settings.get_instance = AsyncMock(return_value=mock_settings)

        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["default_content_processing_engine_doc"] == "auto"
        assert data["default_embedding_option"] == "ask"

    @pytest.mark.asyncio
    @patch("api.routers.settings.ContentSettings")
    async def test_update_settings(self, mock_content_settings, client):
        """Test PUT /api/settings updates settings."""
        mock_settings = MagicMock()
        mock_settings.default_content_processing_engine_doc = "docling"
        mock_settings.default_content_processing_engine_url = "firecrawl"
        mock_settings.default_embedding_option = "always"
        mock_settings.auto_delete_files = "no"
        mock_settings.youtube_preferred_languages = ["en", "es"]
        mock_settings.update = AsyncMock()

        mock_content_settings.get_instance = AsyncMock(return_value=mock_settings)

        response = client.put(
            "/api/settings",
            json={
                "default_content_processing_engine_doc": "docling",
                "default_embedding_option": "always",
            },
        )
        assert response.status_code == 200
        mock_settings.update.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routers.settings.ContentSettings")
    async def test_update_settings_partial(self, mock_content_settings, client):
        """Test PUT /api/settings updates only provided fields."""
        mock_settings = MagicMock()
        mock_settings.default_content_processing_engine_doc = "auto"
        mock_settings.default_embedding_option = "ask"
        mock_settings.update = AsyncMock()

        mock_content_settings.get_instance = AsyncMock(return_value=mock_settings)

        response = client.put(
            "/api/settings",
            json={"default_embedding_option": "never"},
        )
        assert response.status_code == 200
        assert mock_settings.default_embedding_option == "never"

    @pytest.mark.asyncio
    @patch("api.routers.settings.ContentSettings")
    async def test_update_settings_error(self, mock_content_settings, client):
        """Test PUT /api/settings handles errors."""
        from open_notebook.exceptions import InvalidInputError

        mock_settings = MagicMock()
        mock_content_settings.get_instance = AsyncMock(return_value=mock_settings)
        mock_settings.update = AsyncMock(side_effect=InvalidInputError("Invalid value"))

        response = client.put(
            "/api/settings",
            json={"default_embedding_option": "invalid"},
        )
        assert response.status_code == 400
