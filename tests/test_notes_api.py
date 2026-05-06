from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.auth import CurrentUser
from api.models import ResourceCapabilities


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestNoteCreation:
    """Test suite for Note API endpoints."""

    @patch("api.routers.notes.Note")
    def test_create_note_returns_command_id(self, mock_note_cls, client):
        """Test that creating a note returns the embed command_id."""
        mock_note = AsyncMock()
        mock_note.id = "note:abc123"
        mock_note.title = "Test Note"
        mock_note.content = "Some content"
        mock_note.note_type = "human"
        mock_note.created = "2026-01-01T00:00:00Z"
        mock_note.updated = "2026-01-01T00:00:00Z"
        mock_note.save.return_value = "command:embed123"
        mock_note.add_to_notebook = AsyncMock()
        mock_note_cls.return_value = mock_note

        response = client.post(
            "/api/notes",
            json={"content": "Some content", "note_type": "human"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["command_id"] == "command:embed123"
        assert data["id"] == "note:abc123"

    @patch("api.routers.notes.Note")
    def test_create_note_command_id_none_when_no_content_embedding(
        self, mock_note_cls, client
    ):
        """Test that command_id is None when save returns None (no embedding)."""
        mock_note = AsyncMock()
        mock_note.id = "note:abc456"
        mock_note.title = "Empty Note"
        mock_note.content = "Some content"
        mock_note.note_type = "human"
        mock_note.created = "2026-01-01T00:00:00Z"
        mock_note.updated = "2026-01-01T00:00:00Z"
        mock_note.save.return_value = None
        mock_note.add_to_notebook = AsyncMock()
        mock_note_cls.return_value = mock_note

        response = client.post(
            "/api/notes",
            json={"content": "Some content", "note_type": "human"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["command_id"] is None


class TestNoteUpdate:
    """Test suite for Note update endpoint."""

    @patch("api.routers.notes.Note")
    def test_update_note_returns_command_id(self, mock_note_cls, client):
        """Test that updating a note returns the embed command_id."""
        mock_note = AsyncMock()
        mock_note.id = "note:abc123"
        mock_note.title = "Test Note"
        mock_note.content = "Original content"
        mock_note.note_type = "human"
        mock_note.created = "2026-01-01T00:00:00Z"
        mock_note.updated = "2026-01-01T00:00:00Z"
        mock_note.save.return_value = "command:embed789"
        mock_note_cls.get = AsyncMock(return_value=mock_note)

        response = client.put(
            "/api/notes/note:abc123",
            json={"content": "Updated content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["command_id"] == "command:embed789"

    @patch("api.routers.notes.Note")
    def test_update_note_command_id_none_when_no_embedding(
        self, mock_note_cls, client
    ):
        """Test that command_id is None on update when no embedding is triggered."""
        mock_note = AsyncMock()
        mock_note.id = "note:abc123"
        mock_note.title = "Test Note"
        mock_note.content = "Some content"
        mock_note.note_type = "human"
        mock_note.created = "2026-01-01T00:00:00Z"
        mock_note.updated = "2026-01-01T00:00:00Z"
        mock_note.save.return_value = None
        mock_note_cls.get = AsyncMock(return_value=mock_note)

        response = client.put(
            "/api/notes/note:abc123",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["command_id"] is None


class TestNoteWorkspacePermissions:
    def actor(self) -> CurrentUser:
        return CurrentUser(id="app_user:member", username="member", role="user")

    @patch("api.routers.notes.current_user_from_request")
    @patch("api.routers.notes.resolve_resource_capabilities", new_callable=AsyncMock)
    @patch("api.routers.notes.Notebook")
    @patch("api.routers.notes.Note")
    def test_create_note_requires_notebook_create_note_capability(
        self, mock_note_cls, mock_notebook_cls, mock_caps, mock_current_user, client
    ):
        mock_current_user.return_value = self.actor()
        mock_notebook_cls.get = AsyncMock(
            return_value=type(
                "NotebookStub",
                (),
                {
                    "owner_id": "app_user:owner",
                    "workspace_id": "workspace:team",
                    "visibility": "private",
                },
            )()
        )
        mock_caps.return_value = ResourceCapabilities(can_read=True, can_create_note=False)

        response = client.post(
            "/api/notes",
            json={
                "content": "Team note",
                "note_type": "human",
                "notebook_id": "notebook:team",
            },
        )

        assert response.status_code == 403
        mock_note_cls.assert_not_called()

    @patch("api.routers.notes.current_user_from_request")
    @patch("api.routers.notes.resolve_resource_capabilities", new_callable=AsyncMock)
    @patch("api.routers.notes.Notebook")
    def test_list_notes_requires_notebook_read_capability(
        self, mock_notebook_cls, mock_caps, mock_current_user, client
    ):
        mock_current_user.return_value = self.actor()
        mock_notebook_cls.get = AsyncMock(
            return_value=type(
                "NotebookStub",
                (),
                {
                    "owner_id": "app_user:owner",
                    "workspace_id": "workspace:team",
                    "visibility": "private",
                },
            )()
        )
        mock_caps.return_value = ResourceCapabilities(can_read=False)

        response = client.get("/api/notes", params={"notebook_id": "notebook:team"})

        assert response.status_code == 403

    @patch("api.routers.notes.current_user_from_request")
    @patch("api.routers.notes.resolve_resource_capabilities", new_callable=AsyncMock)
    @patch("api.routers.notes.Note")
    def test_update_note_requires_note_update_capability(
        self, mock_note_cls, mock_caps, mock_current_user, client
    ):
        mock_current_user.return_value = self.actor()
        mock_note = AsyncMock()
        mock_note.id = "note:abc123"
        mock_note.title = "Team Note"
        mock_note.content = "Original"
        mock_note.note_type = "human"
        mock_note.owner_id = "app_user:other"
        mock_note.workspace_id = "workspace:team"
        mock_note.created = "2026-01-01T00:00:00Z"
        mock_note.updated = "2026-01-01T00:00:00Z"
        mock_note_cls.get = AsyncMock(return_value=mock_note)
        mock_caps.return_value = ResourceCapabilities(can_read=True, can_update=False)

        response = client.put("/api/notes/note:abc123", json={"content": "Updated"})

        assert response.status_code == 403
        mock_note.save.assert_not_awaited()

    @patch("api.routers.notes.current_user_from_request")
    @patch("api.routers.notes.resolve_resource_capabilities", new_callable=AsyncMock)
    @patch("api.routers.notes.Note")
    def test_delete_note_uses_note_delete_capability(
        self, mock_note_cls, mock_caps, mock_current_user, client
    ):
        mock_current_user.return_value = self.actor()
        mock_note = AsyncMock()
        mock_note.id = "note:abc123"
        mock_note.owner_id = "app_user:member"
        mock_note.workspace_id = "workspace:team"
        mock_note.visibility = "private"
        mock_note_cls.get = AsyncMock(return_value=mock_note)
        mock_caps.return_value = ResourceCapabilities(can_read=True, can_delete=True)

        response = client.delete("/api/notes/note:abc123")

        assert response.status_code == 200
        mock_note.delete.assert_awaited_once()
