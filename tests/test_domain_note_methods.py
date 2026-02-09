"""
Additional tests for Note domain model methods.

Covers save(), add_to_notebook(), and get_context() variations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest

from open_notebook.domain.notebook import Note
from open_notebook.exceptions import InvalidInputError


class TestNoteMethods:
    """Test suite for Note methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    @patch("open_notebook.domain.base.repo_create")
    async def test_save_submits_embed_command(self, mock_repo_create, mock_submit_command):
        """Test Note.save() submits embed_note command when content exists."""
        note = Note(title="Test Note", content="Some content")
        note.id = None

        mock_repo_create.return_value = {
            "id": "note:123",
            "title": "Test Note",
            "content": "Some content",
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }
        mock_submit_command.return_value = "command:456"

        command_id = await note.save()
        assert command_id == "command:456"
        mock_submit_command.assert_called_once_with(
            "open_notebook", "embed_note", {"note_id": "note:123"}
        )

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_create")
    async def test_save_no_content_no_embed(self, mock_repo_create):
        """Test Note.save() does not submit embed command when content is None."""
        note = Note(title="Test Note", content=None)
        note.id = None

        mock_repo_create.return_value = {
            "id": "note:123",
            "title": "Test Note",
            "content": None,
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }

        with patch("open_notebook.domain.notebook.submit_command") as mock_submit:
            command_id = await note.save()
            assert command_id is None
            mock_submit.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_empty_content_no_embed(self):
        """Test that empty/whitespace-only content is rejected at construction."""
        with pytest.raises(InvalidInputError):
            Note(title="Test Note", content="   ")  # Whitespace only

    @pytest.mark.asyncio
    async def test_add_to_notebook_empty_id(self):
        """Test Note.add_to_notebook() raises error for empty notebook_id."""
        note = Note(title="Test", content="Content")
        note.id = "note:123"

        with pytest.raises(InvalidInputError, match="Notebook ID must be provided"):
            await note.add_to_notebook("")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_relate")
    async def test_add_to_notebook_success(self, mock_repo_relate):
        """Test Note.add_to_notebook() creates artifact relationship."""
        note = Note(title="Test", content="Content")
        note.id = "note:123"

        mock_repo_relate.return_value = True

        result = await note.add_to_notebook("notebook:456")
        assert result is True
        mock_repo_relate.assert_called_once_with(
            source="note:123", relationship="artifact", target="notebook:456", data={}
        )

    def test_get_context_short(self):
        """Test Note.get_context(context_size='short') truncates content."""
        note = Note(title="Test Note", content="A" * 200)
        context = note.get_context(context_size="short")
        assert isinstance(context, dict)
        assert len(context.get("content", "")) <= 100  # Should be truncated

    def test_get_context_long(self):
        """Test Note.get_context(context_size='long') includes full content."""
        content = "This is the full note content that should be included."
        note = Note(title="Test Note", content=content)
        context = note.get_context(context_size="long")
        assert isinstance(context, dict)
        assert context.get("content") == content

    def test_get_context_no_content(self):
        """Test Note.get_context() handles None content."""
        note = Note(title="Test Note", content=None)
        context = note.get_context()
        assert isinstance(context, dict)
        assert context.get("title") == "Test Note"
        assert context.get("content") is None

    def test_get_context_default_short(self):
        """Test Note.get_context() defaults to short."""
        note = Note(title="Test", content="A" * 200)
        context_default = note.get_context()
        context_short = note.get_context(context_size="short")
        # Both should be truncated
        assert isinstance(context_default, dict)
        assert isinstance(context_short, dict)
        assert len(context_default.get("content", "")) <= 100
        assert len(context_short.get("content", "")) <= 100
