"""
Additional tests for Source domain model methods.

Covers get_status, get_processing_progress, get_insights, and other methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.domain.notebook import Source, SourceInsight, SourceEmbedding
from open_notebook.exceptions import DatabaseOperationError


class TestSourceMethods:
    """Test suite for Source methods not covered in other tests."""

    @pytest.mark.asyncio
    @patch("surreal_commands.get_command_status")
    async def test_get_status_completed(self, mock_get_command_status):
        """Test Source.get_status() returns status for completed job."""
        source = Source(title="Test", topics=[])
        source.command = "command:123"

        mock_status = MagicMock()
        mock_status.status = "completed"
        mock_get_command_status.return_value = mock_status

        status = await source.get_status()
        assert status == "completed"

    @pytest.mark.asyncio
    @patch("surreal_commands.get_command_status")
    async def test_get_status_running(self, mock_get_command_status):
        """Test Source.get_status() returns status for running job."""
        source = Source(title="Test", topics=[])
        source.command = "command:123"

        mock_status = MagicMock()
        mock_status.status = "running"
        mock_get_command_status.return_value = mock_status

        status = await source.get_status()
        assert status == "running"

    @pytest.mark.asyncio
    async def test_get_status_no_command(self):
        """Test Source.get_status() returns None when no command."""
        source = Source(title="Test", topics=[])
        source.command = None

        status = await source.get_status()
        assert status is None

    @pytest.mark.asyncio
    @patch("surreal_commands.get_command_status")
    async def test_get_processing_progress(self, mock_get_command_status):
        """Test Source.get_processing_progress() returns progress."""
        source = Source(title="Test", topics=[])
        source.command = "command:123"

        mock_status = MagicMock()
        mock_status.status = "running"
        mock_status.result = {"execution_metadata": {"started_at": "2024-01-01T00:00:00"}}
        mock_get_command_status.return_value = mock_status

        progress = await source.get_processing_progress()
        assert isinstance(progress, dict)
        assert progress["status"] == "running"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_insights_success(self, mock_repo_query):
        """Test Source.get_insights() returns list of insights."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        # repo_query returns list of dicts directly, not nested under "insight"
        mock_repo_query.return_value = [
            {
                "id": "insight:1",
                "insight_type": "summary",
                "content": "Summary text",
            }
        ]

        insights = await source.get_insights()
        assert len(insights) == 1
        assert insights[0].insight_type == "summary"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_insights_empty(self, mock_repo_query):
        """Test Source.get_insights() returns empty list."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        mock_repo_query.return_value = []

        insights = await source.get_insights()
        assert insights == []

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_insights_error(self, mock_repo_query):
        """Test Source.get_insights() raises DatabaseOperationError on error."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        mock_repo_query.side_effect = Exception("DB error")

        with pytest.raises(DatabaseOperationError):
            await source.get_insights()


class TestSourceInsightMethods:
    """Test suite for SourceInsight methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_source_success(self, mock_repo_query):
        """Test SourceInsight.get_source() returns parent source."""
        insight = SourceInsight(insight_type="summary", content="Content")
        insight.id = "insight:123"

        mock_repo_query.return_value = [
            {
                "source": {
                    "id": "source:456",
                    "title": "Parent Source",
                    "topics": [],
                    "asset": None,
                }
            }
        ]

        source = await insight.get_source()
        assert source.title == "Parent Source"
        assert source.id == "source:456"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_source_error(self, mock_repo_query):
        """Test SourceInsight.get_source() raises DatabaseOperationError on error."""
        insight = SourceInsight(insight_type="summary", content="Content")
        insight.id = "insight:123"

        mock_repo_query.side_effect = Exception("DB error")

        with pytest.raises(DatabaseOperationError):
            await insight.get_source()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Note")
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_save_as_note_with_notebook(
        self, mock_repo_query, mock_note_class
    ):
        """Test SourceInsight.save_as_note() creates note and links to notebook."""
        insight = SourceInsight(insight_type="summary", content="Summary content")
        insight.id = "insight:123"

        mock_repo_query.return_value = [
            {
                "source": {
                    "id": "source:456",
                    "title": "Parent Source",
                    "topics": [],
                    "asset": None,
                }
            }
        ]

        mock_note = MagicMock()
        mock_note.id = "note:789"
        mock_note.save = AsyncMock()
        mock_note.add_to_notebook = AsyncMock()
        mock_note_class.return_value = mock_note

        note = await insight.save_as_note(notebook_id="notebook:1")
        assert note is not None
        mock_note.save.assert_called_once()
        mock_note.add_to_notebook.assert_called_once_with("notebook:1")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Note")
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_save_as_note_without_notebook(
        self, mock_repo_query, mock_note_class
    ):
        """Test SourceInsight.save_as_note() creates note without notebook link."""
        insight = SourceInsight(insight_type="summary", content="Summary content")
        insight.id = "insight:123"

        mock_repo_query.return_value = [
            {
                "source": {
                    "id": "source:456",
                    "title": "Parent Source",
                    "topics": [],
                    "asset": None,
                }
            }
        ]

        mock_note = MagicMock()
        mock_note.id = "note:789"
        mock_note.save = AsyncMock()
        mock_note_class.return_value = mock_note

        note = await insight.save_as_note()
        assert note is not None
        mock_note.save.assert_called_once()


class TestSourceEmbeddingMethods:
    """Test suite for SourceEmbedding methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_source_success(self, mock_repo_query):
        """Test SourceEmbedding.get_source() returns parent source."""
        embedding = SourceEmbedding(content="embedding content")
        embedding.id = "embedding:123"

        mock_repo_query.return_value = [
            {
                "source": {
                    "id": "source:456",
                    "title": "Parent Source",
                    "topics": [],
                    "asset": None,
                }
            }
        ]

        source = await embedding.get_source()
        assert source.title == "Parent Source"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_source_error(self, mock_repo_query):
        """Test SourceEmbedding.get_source() raises DatabaseOperationError on error."""
        embedding = SourceEmbedding(content="content")
        embedding.id = "embedding:123"

        mock_repo_query.side_effect = Exception("DB error")

        with pytest.raises(DatabaseOperationError):
            await embedding.get_source()
