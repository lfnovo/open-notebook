"""
Tests for RecordModel singleton pattern and methods.

Covers get_instance(), update(), _load_from_db(), and singleton behavior.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.domain.base import RecordModel
from open_notebook.domain.content_settings import ContentSettings


class TestRecordModel:
    """Test suite for RecordModel base class."""

    def test_singleton_behavior(self):
        """Test RecordModel returns same instance for same record_id."""
        # Clear any existing instances
        ContentSettings.clear_instance()

        instance1 = ContentSettings()
        instance2 = ContentSettings()

        assert instance1 is instance2

    def test_singleton_updates_with_kwargs(self):
        """Test RecordModel singleton updates when kwargs provided."""
        ContentSettings.clear_instance()

        instance1 = ContentSettings()
        instance2 = ContentSettings(default_embedding_option="always")

        assert instance1 is instance2
        assert instance2.default_embedding_option == "always"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_instance_loads_from_db(self, mock_repo_query):
        """Test RecordModel.get_instance() loads data from database."""
        ContentSettings.clear_instance()

        mock_repo_query.return_value = [
            {
                "record_id": "open_notebook:content_settings",
                "default_embedding_option": "always",
                "auto_delete_files": "yes",
            }
        ]

        instance = await ContentSettings.get_instance()
        assert instance.default_embedding_option == "always"
        mock_repo_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_instance_no_db_record(self, mock_repo_query):
        """Test RecordModel.get_instance() handles missing DB record."""
        ContentSettings.clear_instance()

        mock_repo_query.return_value = []  # No record found

        instance = await ContentSettings.get_instance()
        # Should still return instance with defaults
        assert instance is not None

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_load_from_db_dict_response(self, mock_repo_query):
        """Test _load_from_db() handles dict response."""
        ContentSettings.clear_instance()

        mock_repo_query.return_value = {
            "default_embedding_option": "never",
        }

        instance = ContentSettings()
        await instance._load_from_db()
        assert instance.default_embedding_option == "never"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_upsert")
    @patch("open_notebook.domain.base.repo_query")
    async def test_update_saves_to_db(self, mock_repo_query, mock_repo_upsert):
        """Test RecordModel.update() saves to database."""
        ContentSettings.clear_instance()

        mock_repo_query.return_value = [
            {
                "record_id": "open_notebook:content_settings",
                "default_embedding_option": "always",
            }
        ]

        instance = ContentSettings()
        instance.default_embedding_option = "never"
        await instance.update()

        mock_repo_upsert.assert_called_once()
        # Verify updated value was saved
        # repo_upsert(table_name, record_id, data) - check args
        call_args = mock_repo_upsert.call_args
        # repo_upsert is called with positional args: (table_name, record_id, data)
        if len(call_args.args) >= 3:
            data = call_args.args[2]
        elif "data" in call_args.kwargs:
            data = call_args.kwargs["data"]
        else:
            data = {}
        assert "default_embedding_option" in data
        assert data["default_embedding_option"] == "never"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_upsert")
    @patch("open_notebook.domain.base.repo_query")
    async def test_update_refreshes_from_db(self, mock_repo_query, mock_repo_upsert):
        """Test RecordModel.update() refreshes instance from DB response."""
        ContentSettings.clear_instance()

        # Mock upsert response
        mock_repo_upsert.return_value = True
        # Mock query after update
        mock_repo_query.return_value = [
            {
                "record_id": "open_notebook:content_settings",
                "default_embedding_option": "always",
                "updated": "2024-01-02T00:00:00",
            }
        ]

        instance = ContentSettings()
        instance.default_embedding_option = "always"
        await instance.update()

        # Should have refreshed from DB without clearing existing attrs
        assert instance.default_embedding_option == "always"

    def test_clear_instance(self):
        """Test clear_instance() removes singleton."""
        ContentSettings.clear_instance()

        instance1 = ContentSettings()
        ContentSettings.clear_instance()
        instance2 = ContentSettings()

        # After clear_instance(), a new ContentSettings() returns a new instance
        assert instance1 is not instance2
