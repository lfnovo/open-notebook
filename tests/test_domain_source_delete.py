"""
Tests for Source.delete() method.

Covers file cleanup, embedding deletion, and insight deletion.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import os

import pytest

from open_notebook.domain.notebook import Asset, Source
from open_notebook.exceptions import DatabaseOperationError


class TestSourceDelete:
    """Test suite for Source.delete() cleanup behavior."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    @patch("open_notebook.domain.notebook.os.unlink")
    async def test_delete_removes_file(self, mock_unlink, mock_repo_delete, mock_repo_query):
        """Test Source.delete() removes associated file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(b"test content")

        try:
            source = Source(
                title="Test Source",
                topics=[],
                asset=Asset(file_path=tmp_path),
            )
            source.id = "source:123"

            mock_repo_query.return_value = []  # No embeddings/insights
            mock_repo_delete.return_value = True

            result = await source.delete()
            assert result is True
            mock_unlink.assert_called_once_with(Path(tmp_path))

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    async def test_delete_handles_missing_file(self, mock_repo_delete, mock_repo_query):
        """Test Source.delete() continues if file doesn't exist."""
        source = Source(
            title="Test Source",
            topics=[],
            asset=Asset(file_path="/nonexistent/file.pdf"),
        )
        source.id = "source:123"

        mock_repo_query.return_value = []
        mock_repo_delete.return_value = True

        result = await source.delete()
        assert result is True  # Should complete successfully

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    @patch("open_notebook.domain.notebook.os.unlink")
    async def test_delete_handles_file_error(self, mock_unlink, mock_repo_delete, mock_repo_query):
        """Test Source.delete() continues if file deletion fails."""
        source = Source(
            title="Test Source",
            topics=[],
            asset=Asset(file_path="/some/file.pdf"),
        )
        source.id = "source:123"

        mock_unlink.side_effect = PermissionError("Permission denied")
        mock_repo_query.return_value = []
        mock_repo_delete.return_value = True

        # Should log warning but continue
        result = await source.delete()
        assert result is True

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    async def test_delete_removes_embeddings(self, mock_repo_delete, mock_repo_query):
        """Test Source.delete() removes associated embeddings."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        def query_side_effect(query, params):
            if "DELETE source_embedding" in query:
                return []  # Delete successful
            elif "DELETE source_insight" in query:
                return []  # Delete successful
            return []

        mock_repo_query.side_effect = query_side_effect
        mock_repo_delete.return_value = True

        result = await source.delete()
        assert result is True

        # Verify both DELETE queries were called
        delete_calls = [call for call in mock_repo_query.call_args_list if "DELETE" in str(call)]
        assert len(delete_calls) >= 2  # embeddings and insights

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    async def test_delete_handles_embedding_error(self, mock_repo_delete, mock_repo_query):
        """Test Source.delete() continues if embedding deletion fails."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        def query_side_effect(query, params):
            if "DELETE source_embedding" in query:
                raise Exception("DB error")
            return []

        mock_repo_query.side_effect = query_side_effect
        mock_repo_delete.return_value = True

        # Should log warning but continue
        result = await source.delete()
        assert result is True

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    async def test_delete_no_asset(self, mock_repo_delete, mock_repo_query):
        """Test Source.delete() works when source has no asset."""
        source = Source(title="Test", topics=[], asset=None)
        source.id = "source:123"

        mock_repo_query.return_value = []
        mock_repo_delete.return_value = True

        result = await source.delete()
        assert result is True

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.base.repo_delete")
    async def test_delete_no_file_path(self, mock_repo_delete, mock_repo_query):
        """Test Source.delete() works when asset has no file_path."""
        source = Source(
            title="Test",
            topics=[],
            asset=Asset(file_path=None, url="https://example.com"),
        )
        source.id = "source:123"

        mock_repo_query.return_value = []
        mock_repo_delete.return_value = True

        result = await source.delete()
        assert result is True
