"""
Edge case tests for Source domain model methods.

Covers error paths and boundary conditions for Source methods.
"""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import Source
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError


class TestSourceEdgeCases:
    """Test suite for Source edge cases."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_vectorize_no_full_text(self, mock_submit_command):
        """Test Source.vectorize() raises ValueError when full_text is None."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"
        source.full_text = None

        # ValueError gets wrapped in DatabaseOperationError
        with pytest.raises((ValueError, DatabaseOperationError)):
            await source.vectorize()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_vectorize_empty_full_text(self, mock_submit_command):
        """Test Source.vectorize() raises ValueError when full_text is empty."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"
        source.full_text = ""

        # ValueError gets wrapped in DatabaseOperationError
        with pytest.raises((ValueError, DatabaseOperationError)):
            await source.vectorize()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_vectorize_submission_error(self, mock_submit_command):
        """Test Source.vectorize() raises DatabaseOperationError on submission failure."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"
        source.full_text = "Some text"

        mock_submit_command.side_effect = Exception("Submission failed")

        with pytest.raises(DatabaseOperationError):
            await source.vectorize()

    @pytest.mark.asyncio
    async def test_add_insight_empty_type(self):
        """Test Source.add_insight() raises InvalidInputError for empty type."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        with pytest.raises(InvalidInputError, match="Insight type and content must be provided"):
            await source.add_insight("", "Content")

    @pytest.mark.asyncio
    async def test_add_insight_empty_content(self):
        """Test Source.add_insight() raises InvalidInputError for empty content."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        with pytest.raises(InvalidInputError, match="Insight type and content must be provided"):
            await source.add_insight("summary", "")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_add_insight_success(self, mock_submit_command):
        """Test Source.add_insight() submits command successfully."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        mock_submit_command.return_value = "command:789"

        command_id = await source.add_insight("summary", "Summary content")
        assert command_id == "command:789"
        mock_submit_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_notebook_empty_id(self):
        """Test Source.add_to_notebook() raises InvalidInputError for empty notebook_id."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        with pytest.raises(InvalidInputError, match="Notebook ID must be provided"):
            await source.add_to_notebook("")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_relate")
    async def test_add_to_notebook_success(self, mock_repo_relate):
        """Test Source.add_to_notebook() creates relationship."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        mock_repo_relate.return_value = True

        result = await source.add_to_notebook("notebook:456")
        assert result is True
        mock_repo_relate.assert_called_once_with(
            source="source:123", relationship="reference", target="notebook:456", data={}
        )

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_context_with_topics(self, mock_repo_query):
        """Test Source.get_context() includes topics."""
        source = Source(title="Test Source", topics=["AI", "Machine Learning"])
        source.id = "source:123"
        source.full_text = "Some content"

        mock_repo_query.return_value = []  # No insights

        context = await source.get_context()
        assert isinstance(context, dict)
        assert context.get("title") == "Test Source"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_context_short_truncates(self, mock_repo_query):
        """Test Source.get_context(context_size='short') doesn't include full_text."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"
        source.full_text = "A" * 200  # Long text

        mock_repo_query.return_value = []  # No insights

        context = await source.get_context(context_size="short")
        assert isinstance(context, dict)
        assert "full_text" not in context  # Short doesn't include full_text

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_context_long_includes_all(self, mock_repo_query):
        """Test Source.get_context(context_size='long') includes full text."""
        long_text = "This is a very long text content. " * 10
        source = Source(title="Test", topics=[], full_text=long_text)
        source.id = "source:123"

        mock_repo_query.return_value = []  # No insights

        context = await source.get_context(context_size="long")
        assert isinstance(context, dict)
        assert "full_text" in context  # Long includes full_text
        assert context["full_text"] == long_text
