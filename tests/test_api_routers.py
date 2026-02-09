"""
Tests for API router endpoints.

Focuses on notebooks and notes routers which have low coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from api.main import app

    return TestClient(app)


class TestNotebooksRouter:
    """Test suite for /api/notebooks endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.repo_query")
    async def test_get_notebooks_success(self, mock_repo_query, client):
        """Test GET /api/notebooks returns list of notebooks."""
        mock_repo_query.return_value = [
            {
                "id": "notebook:1",
                "name": "Test Notebook",
                "description": "Test",
                "archived": False,
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
                "source_count": 5,
                "note_count": 3,
            }
        ]

        response = client.get("/api/notebooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Notebook"
        assert data[0]["source_count"] == 5

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.repo_query")
    async def test_get_notebooks_filter_archived(self, mock_repo_query, client):
        """Test GET /api/notebooks?archived=true filters archived notebooks."""
        mock_repo_query.return_value = [
            {
                "id": "notebook:1",
                "name": "Active",
                "archived": False,
                "source_count": 0,
                "note_count": 0,
            },
            {
                "id": "notebook:2",
                "name": "Archived",
                "archived": True,
                "source_count": 0,
                "note_count": 0,
            },
        ]

        response = client.get("/api/notebooks?archived=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["archived"] is True

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.repo_query")
    async def test_get_notebooks_custom_order(self, mock_repo_query, client):
        """Test GET /api/notebooks?order_by=name asc uses custom ordering."""
        mock_repo_query.return_value = []

        response = client.get("/api/notebooks?order_by=name asc")
        assert response.status_code == 200
        # Verify order_by was used in query
        call_args = mock_repo_query.call_args[0][0]
        assert "ORDER BY name asc" in call_args

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.Notebook")
    async def test_create_notebook_success(self, mock_notebook_class, client):
        """Test POST /api/notebooks creates a new notebook."""
        mock_notebook = MagicMock()
        mock_notebook.id = "notebook:123"
        mock_notebook.name = "New Notebook"
        mock_notebook.description = "Description"
        mock_notebook.archived = False
        mock_notebook.created = "2024-01-01T00:00:00"
        mock_notebook.updated = "2024-01-01T00:00:00"
        mock_notebook.save = AsyncMock()

        mock_notebook_class.return_value = mock_notebook

        response = client.post(
            "/api/notebooks", json={"name": "New Notebook", "description": "Description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Notebook"
        assert data["id"] == "notebook:123"

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.Notebook")
    async def test_create_notebook_invalid_input(self, mock_notebook_class, client):
        """Test POST /api/notebooks returns 400 for invalid input."""
        mock_notebook_class.side_effect = Exception("Invalid name")

        from open_notebook.exceptions import InvalidInputError

        mock_notebook_class.side_effect = InvalidInputError("Name cannot be empty")

        response = client.post("/api/notebooks", json={"name": "", "description": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.Notebook")
    async def test_get_notebook_delete_preview(self, mock_notebook_class, client):
        """Test GET /api/notebooks/{id}/delete-preview returns preview."""
        mock_notebook = MagicMock()
        mock_notebook.get_delete_preview = AsyncMock(
            return_value={
                "note_count": 5,
                "exclusive_source_count": 2,
                "shared_source_count": 1,
            }
        )
        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)

        response = client.get("/api/notebooks/notebook:123/delete-preview")
        assert response.status_code == 200
        data = response.json()
        assert data["note_count"] == 5
        assert data["exclusive_source_count"] == 2
        assert data["shared_source_count"] == 1

    @pytest.mark.asyncio
    @patch("api.routers.notebooks.Notebook")
    async def test_get_notebook_delete_preview_not_found(self, mock_notebook_class, client):
        """Test GET /api/notebooks/{id}/delete-preview returns 404 for missing notebook."""
        from open_notebook.exceptions import NotFoundError

        mock_notebook_class.get = AsyncMock(side_effect=NotFoundError("Not found"))

        response = client.get("/api/notebooks/notebook:999/delete-preview")
        assert response.status_code == 404


class TestNotesRouter:
    """Test suite for /api/notes endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_get_notes_all(self, mock_note_class, client):
        """Test GET /api/notes returns all notes."""
        mock_note = MagicMock()
        mock_note.id = "note:1"
        mock_note.title = "Test Note"
        mock_note.content = "Content"
        mock_note.note_type = "human"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"

        mock_note_class.get_all = AsyncMock(return_value=[mock_note])

        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Note"

    @pytest.mark.asyncio
    @patch("api.routers.notes.Notebook")
    async def test_get_notes_by_notebook(self, mock_notebook_class, client):
        """Test GET /api/notes?notebook_id=X returns notes for notebook."""
        mock_notebook = MagicMock()
        mock_note = MagicMock()
        mock_note.id = "note:1"
        mock_note.title = "Note"
        mock_note.content = "Content"
        mock_note.note_type = "human"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"
        mock_notebook.get_notes = AsyncMock(return_value=[mock_note])

        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)

        response = client.get("/api/notes?notebook_id=notebook:123")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_create_note_success(self, mock_note_class, client):
        """Test POST /api/notes creates a new note."""
        mock_note = MagicMock()
        mock_note.id = "note:123"
        mock_note.title = "New Note"
        mock_note.content = "Content"
        mock_note.note_type = "human"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"
        mock_note.save = AsyncMock()

        mock_note_class.return_value = mock_note

        response = client.post(
            "/api/notes",
            json={"title": "New Note", "content": "Content", "note_type": "human"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Note"

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_create_note_invalid_type(self, mock_note_class, client):
        """Test POST /api/notes returns 400 for invalid note_type."""
        response = client.post(
            "/api/notes",
            json={"title": "Note", "content": "Content", "note_type": "invalid"},
        )
        assert response.status_code == 400
        assert "must be 'human' or 'ai'" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_get_note_by_id(self, mock_note_class, client):
        """Test GET /api/notes/{id} returns specific note."""
        mock_note = MagicMock()
        mock_note.id = "note:123"
        mock_note.title = "Test Note"
        mock_note.content = "Content"
        mock_note.note_type = "human"
        mock_note.created = "2024-01-01T00:00:00"
        mock_note.updated = "2024-01-01T00:00:00"

        mock_note_class.get = AsyncMock(return_value=mock_note)

        response = client.get("/api/notes/note:123")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Note"

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_update_note(self, mock_note_class, client):
        """Test PUT /api/notes/{id} updates note."""
        mock_note = MagicMock()
        mock_note.id = "note:123"
        mock_note.title = "Updated Title"
        mock_note.content = "Updated Content"
        mock_note.note_type = "human"
        mock_note.updated = "2024-01-02T00:00:00"
        mock_note.save = AsyncMock()

        mock_note_class.get = AsyncMock(return_value=mock_note)

        response = client.put(
            "/api/notes/note:123",
            json={"title": "Updated Title", "content": "Updated Content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    @patch("api.routers.notes.Note")
    async def test_delete_note(self, mock_note_class, client):
        """Test DELETE /api/notes/{id} deletes note."""
        mock_note = MagicMock()
        mock_note.delete = AsyncMock(return_value=True)

        mock_note_class.get = AsyncMock(return_value=mock_note)

        response = client.delete("/api/notes/note:123")
        assert response.status_code == 200
        mock_note.delete.assert_called_once()
