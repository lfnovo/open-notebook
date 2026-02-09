"""
Additional tests for domain model methods to increase coverage.

Focuses on methods not covered in test_domain.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.domain.notebook import Notebook, Note, Source
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError, NotFoundError


class TestNotebookMethods:
    """Test suite for Notebook methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_sources_success(self, mock_repo_query):
        """Test Notebook.get_sources() returns list of sources."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_query.return_value = [
            {
                "source": {
                    "id": "source:1",
                    "title": "Test Source",
                    "topics": [],
                    "asset": None,
                }
            }
        ]

        sources = await notebook.get_sources()
        assert len(sources) == 1
        assert sources[0].title == "Test Source"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_sources_empty(self, mock_repo_query):
        """Test Notebook.get_sources() returns empty list when no sources."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_query.return_value = []

        sources = await notebook.get_sources()
        assert sources == []

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_sources_error(self, mock_repo_query):
        """Test Notebook.get_sources() raises DatabaseOperationError on error."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_query.side_effect = Exception("DB error")

        with pytest.raises(DatabaseOperationError):
            await notebook.get_sources()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_notes_success(self, mock_repo_query):
        """Test Notebook.get_notes() returns list of notes."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_query.return_value = [
            {
                "note": {
                    "id": "note:1",
                    "title": "Test Note",
                    "content": "Content",
                }
            }
        ]

        notes = await notebook.get_notes()
        assert len(notes) == 1
        assert notes[0].title == "Test Note"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_chat_sessions_success(self, mock_repo_query):
        """Test Notebook.get_chat_sessions() returns list of sessions."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_query.return_value = [
            {
                "chat_session": [
                    {
                        "id": "session:1",
                        "title": "Test Session",
                        "notebook_id": "notebook:123",
                    }
                ]
            }
        ]

        sessions = await notebook.get_chat_sessions()
        assert len(sessions) == 1
        assert sessions[0].title == "Test Session"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_delete_preview(self, mock_repo_query):
        """Test Notebook.get_delete_preview() returns counts."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        # Mock note count query
        def query_side_effect(query, params):
            if "SELECT count()" in query:
                return [{"count": 5}]
            elif "assigned_others" in query:
                return [
                    {"id": "source:1", "assigned_others": 0},
                    {"id": "source:2", "assigned_others": 0},
                    {"id": "source:3", "assigned_others": 2},
                ]
            return []

        mock_repo_query.side_effect = query_side_effect

        preview = await notebook.get_delete_preview()
        assert preview["note_count"] == 5
        assert preview["exclusive_source_count"] == 2
        assert preview["shared_source_count"] == 1

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_delete_preview_empty(self, mock_repo_query):
        """Test Notebook.get_delete_preview() with no items."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        def query_side_effect(query, params):
            if "SELECT count()" in query:
                return [{"count": 0}]
            return []

        mock_repo_query.side_effect = query_side_effect

        preview = await notebook.get_delete_preview()
        assert preview["note_count"] == 0
        assert preview["exclusive_source_count"] == 0
        assert preview["shared_source_count"] == 0

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    @patch("open_notebook.domain.base.repo_delete")
    @patch("open_notebook.domain.notebook.repo_query")
    @patch("open_notebook.domain.notebook.Source")
    async def test_delete_notebook_with_exclusive_sources(
        self, mock_source_class, mock_repo_query, mock_repo_delete, mock_submit_command
    ):
        """Test Notebook.delete() with delete_exclusive_sources=True."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        # Mock note for get_notes()
        mock_note = MagicMock()
        mock_note.delete = AsyncMock()
        
        # Mock source for exclusive source deletion
        mock_source = MagicMock()
        mock_source.delete = AsyncMock()
        mock_source_class.get = AsyncMock(return_value=mock_source)

        def query_side_effect(query, params):
            if "SELECT count()" in query or "count() as count" in query:
                return [{"count": 2}]
            elif "assigned_others" in query:
                return [
                    {"id": "source:1", "assigned_others": 0},
                    {"id": "source:2", "assigned_others": 1},
                ]
            elif "DELETE artifact" in query or "DELETE reference" in query:
                return []
            return []

        mock_repo_query.side_effect = query_side_effect
        
        # Mock get_notes to return our mock note
        notebook.get_notes = AsyncMock(return_value=[mock_note])
        mock_repo_delete.return_value = True

        result = await notebook.delete(delete_exclusive_sources=True)
        assert result["deleted_notes"] == 1  # One note deleted
        assert result["deleted_sources"] == 1  # One exclusive source deleted
        assert result["unlinked_sources"] == 1  # One shared source unlinked

    @pytest.mark.asyncio
    async def test_delete_notebook_no_id(self):
        """Test Notebook.delete() raises error when id is None."""
        notebook = Notebook(name="Test", description="")
        notebook.id = None

        with pytest.raises(InvalidInputError, match="Cannot delete notebook without an ID"):
            await notebook.delete()


class TestObjectModelMethods:
    """Test suite for ObjectModel base class methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_all_with_order_by(self, mock_repo_query):
        """Test ObjectModel.get_all() with order_by parameter."""
        mock_repo_query.return_value = [
            {"id": "notebook:1", "name": "Notebook 1", "description": "", "archived": False},
            {"id": "notebook:2", "name": "Notebook 2", "description": "", "archived": False},
        ]

        notebooks = await Notebook.get_all(order_by="name asc")
        assert len(notebooks) == 2
        mock_repo_query.assert_called_once()
        assert "ORDER BY name asc" in mock_repo_query.call_args[0][0]

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_all_without_order_by(self, mock_repo_query):
        """Test ObjectModel.get_all() without order_by."""
        mock_repo_query.return_value = [
            {"id": "notebook:1", "name": "Notebook 1", "description": "", "archived": False}
        ]

        notebooks = await Notebook.get_all()
        assert len(notebooks) == 1
        assert "ORDER BY" not in mock_repo_query.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_all_from_base_class_raises(self):
        """Test ObjectModel.get_all() raises when called from base class."""
        with pytest.raises(InvalidInputError, match="must be called from a specific model class"):
            await ObjectModel.get_all()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_by_id_success(self, mock_repo_query):
        """Test ObjectModel.get() retrieves object by ID."""
        mock_repo_query.return_value = [
            {"id": "notebook:123", "name": "Test Notebook", "description": "", "archived": False}
        ]

        notebook = await Notebook.get("notebook:123")
        assert notebook.name == "Test Notebook"
        assert notebook.id == "notebook:123"

    @pytest.mark.asyncio
    async def test_get_empty_id_raises(self):
        """Test ObjectModel.get() raises error for empty ID."""
        with pytest.raises(InvalidInputError, match="ID cannot be empty"):
            await Notebook.get("")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_not_found_raises(self, mock_repo_query):
        """Test ObjectModel.get() raises NotFoundError when not found."""
        mock_repo_query.return_value = []

        with pytest.raises(NotFoundError):
            await Notebook.get("notebook:999")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_polymorphic_resolution(self, mock_repo_query):
        """Test ObjectModel.get() resolves subclass from ID prefix."""
        mock_repo_query.return_value = [
            {"id": "source:123", "title": "Test Source", "topics": [], "asset": None}
        ]

        # Call from ObjectModel base class
        obj = await ObjectModel.get("source:123")
        assert isinstance(obj, Source)
        assert obj.title == "Test Source"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_create")
    async def test_save_new_object(self, mock_repo_create):
        """Test ObjectModel.save() creates new object."""
        notebook = Notebook(name="New Notebook", description="")
        notebook.id = None

        mock_repo_create.return_value = {
            "id": "notebook:123",
            "name": "New Notebook",
            "description": "",
            "archived": False,
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }

        await notebook.save()
        assert notebook.id == "notebook:123"
        mock_repo_create.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_update")
    async def test_save_existing_object(self, mock_repo_update):
        """Test ObjectModel.save() updates existing object."""
        notebook = Notebook(name="Existing Notebook", description="")
        notebook.id = "notebook:123"

        mock_repo_update.return_value = {
            "id": "notebook:123",
            "name": "Updated Notebook",
            "updated": "2024-01-02T00:00:00",
        }

        await notebook.save()
        mock_repo_update.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_delete")
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_delete_success(self, mock_repo_query, mock_repo_delete):
        """Test ObjectModel.delete() removes object."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        # Mock get_notes() which is called by Notebook.delete()
        mock_repo_query.return_value = []
        mock_repo_delete.return_value = True

        result = await notebook.delete()
        assert result is True
        mock_repo_delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_relate")
    async def test_relate_success(self, mock_repo_relate):
        """Test ObjectModel.relate() creates relationship."""
        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:123"

        mock_repo_relate.return_value = True

        result = await notebook.relate("reference", "source:456")
        assert result is True
        mock_repo_relate.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_query")
    async def test_get_all_with_validation_error(self, mock_repo_query):
        """Test ObjectModel.get_all() handles validation errors gracefully."""
        mock_repo_query.return_value = [
            {"id": "notebook:1", "name": "Valid", "description": "", "archived": False},
            {"id": "notebook:2", "invalid": "data"},  # Missing required fields
        ]

        notebooks = await Notebook.get_all()
        # Should only include valid objects (first one has all required fields)
        assert len(notebooks) == 1
        assert notebooks[0].name == "Valid"


class TestSourceMethods:
    """Test suite for Source methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_vectorize_submits_command(self, mock_submit_command):
        """Test Source.vectorize() submits embed_source command."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"
        source.full_text = "Some text to vectorize"  # Must have full_text

        mock_submit_command.return_value = "command:456"

        command_id = await source.vectorize()
        assert command_id == "command:456"
        mock_submit_command.assert_called_once_with(
            "open_notebook", "embed_source", {"source_id": "source:123"}
        )

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.submit_command")
    async def test_add_insight_submits_command(self, mock_submit_command):
        """Test Source.add_insight() submits insight command."""
        source = Source(title="Test", topics=[])
        source.id = "source:123"

        mock_submit_command.return_value = "command:789"

        command_id = await source.add_insight("summarize", "notebook:1")
        assert command_id == "command:789"
        mock_submit_command.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_context_short(self, mock_repo_query):
        """Test Source.get_context() with context_size='short'."""
        source = Source(title="Test Source", topics=["topic1"], full_text="A" * 200)
        source.id = "source:123"
        mock_repo_query.return_value = []  # No insights
        context = await source.get_context(context_size="short")
        assert isinstance(context, dict)
        assert "full_text" not in context  # Short doesn't include full_text

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query")
    async def test_get_context_full(self, mock_repo_query):
        """Test Source.get_context() with context_size='long'."""
        source = Source(title="Test Source", topics=["topic1"], full_text="Full text content")
        source.id = "source:123"
        mock_repo_query.return_value = []  # No insights
        context = await source.get_context(context_size="long")
        assert isinstance(context, dict)
        assert context.get("full_text") == "Full text content"


class TestNoteMethods:
    """Test suite for Note methods."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.base.repo_relate")
    async def test_add_to_notebook(self, mock_repo_relate):
        """Test Note.add_to_notebook() creates relationship."""
        note = Note(title="Test Note", content="Content")
        note.id = "note:123"

        mock_repo_relate.return_value = True

        result = await note.add_to_notebook("notebook:456")
        assert result is True
        mock_repo_relate.assert_called_once()

    def test_get_context_short(self):
        """Test Note.get_context() with context_size='short'."""
        note = Note(title="Test Note", content="A" * 200)
        context = note.get_context(context_size="short")
        assert isinstance(context, dict)
        assert len(context.get("content", "")) <= 100  # Should be truncated

    def test_get_context_full(self):
        """Test Note.get_context() with context_size='long'."""
        note = Note(title="Test Note", content="Full content")
        context = note.get_context(context_size="long")
        assert isinstance(context, dict)
        assert context.get("content") == "Full content"
