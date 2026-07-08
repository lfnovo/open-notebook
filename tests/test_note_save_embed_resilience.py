"""
Tests for Note.save()'s embed_note submission resilience
(open_notebook/domain/notebook.py) and its one caller that needs the
opposite behavior (api/routers/embedding.py).

Note.save()'s embed_note submission is now wrapped in try/except: the note
itself is already durably saved by the time it's attempted (verified
against a live embedded SurrealDB instance - see session notes), so a
transient submission failure shouldn't turn an otherwise-successful save
into a 500, unlike Source.vectorize()/add_insight() which are dedicated
"submit this job" calls with nothing useful to fall back on.

api/routers/embedding.py's POST /embed endpoint is the one exception: for
item_type=note it reuses Note.save() specifically *because* embedding
submission is the explicit point of that call (mirroring
Source.vectorize()) - so it now explicitly checks for a submission failure
(content present, no command_id) and still surfaces it as a failure.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Note


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestNoteSaveEmbedResilience:
    @pytest.mark.asyncio
    async def test_save_does_not_raise_when_submission_fails(self):
        note = Note(title="Test", content="some content")
        with (
            patch(
                "open_notebook.domain.base.ObjectModel.save",
                new=AsyncMock(),
            ),
            patch(
                "open_notebook.domain.notebook.submit_command",
                side_effect=RuntimeError("job queue is down"),
            ),
        ):
            object.__setattr__(note, "id", "note:abc123")
            command_id = await note.save()

        assert command_id is None

    @pytest.mark.asyncio
    async def test_save_still_calls_super_save_before_attempting_submission(self):
        """The note's core save must happen (and succeed) regardless of
        whether the embedding submission afterward fails."""
        note = Note(title="Test", content="some content")
        with (
            patch(
                "open_notebook.domain.base.ObjectModel.save",
                new=AsyncMock(),
            ) as mock_super_save,
            patch(
                "open_notebook.domain.notebook.submit_command",
                side_effect=RuntimeError("job queue is down"),
            ),
        ):
            object.__setattr__(note, "id", "note:abc123")
            await note.save()

        mock_super_save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_returns_command_id_on_success(self):
        note = Note(title="Test", content="some content")
        with (
            patch("open_notebook.domain.base.ObjectModel.save", new=AsyncMock()),
            patch(
                "open_notebook.domain.notebook.submit_command",
                return_value="command:xyz789",
            ),
        ):
            object.__setattr__(note, "id", "note:abc123")
            command_id = await note.save()

        assert command_id == "command:xyz789"

    @pytest.mark.asyncio
    async def test_save_returns_none_when_no_content(self):
        note = Note(title="Test", content=None)
        with (
            patch("open_notebook.domain.base.ObjectModel.save", new=AsyncMock()),
            patch(
                "open_notebook.domain.notebook.submit_command"
            ) as mock_submit,
        ):
            object.__setattr__(note, "id", "note:abc123")
            command_id = await note.save()

        assert command_id is None
        mock_submit.assert_not_called()


class TestEmbeddingEndpointNoteBranch:
    """api/routers/embedding.py: POST /api/embed with item_type=note."""

    def test_returns_500_when_submission_fails_with_content(self, client):
        note = Note(title="Test", content="some content")
        object.__setattr__(note, "id", "note:abc123")

        with (
            patch("api.routers.embedding.Note.get", new=AsyncMock(return_value=note)),
            patch.object(Note, "save", new=AsyncMock(return_value=None)),
            patch(
                "open_notebook.ai.models.model_manager.get_embedding_model",
                new=AsyncMock(return_value=object()),
            ),
        ):
            response = client.post(
                "/api/embed",
                json={"item_id": "note:abc123", "item_type": "note", "async_processing": False},
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to submit note embedding job"

    def test_succeeds_when_submission_works(self, client):
        note = Note(title="Test", content="some content")
        object.__setattr__(note, "id", "note:abc123")

        with (
            patch("api.routers.embedding.Note.get", new=AsyncMock(return_value=note)),
            patch.object(
                Note, "save", new=AsyncMock(return_value="command:abc123")
            ),
            patch(
                "open_notebook.ai.models.model_manager.get_embedding_model",
                new=AsyncMock(return_value=object()),
            ),
        ):
            response = client.post(
                "/api/embed",
                json={"item_id": "note:abc123", "item_type": "note", "async_processing": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["command_id"] == "command:abc123"

    def test_succeeds_with_no_command_id_when_note_has_no_content(self, client):
        """A content-less note has nothing to embed - save() correctly
        returns None, and that must NOT be treated as a submission failure."""
        note = Note(title="Test", content=None)
        object.__setattr__(note, "id", "note:abc123")

        with (
            patch("api.routers.embedding.Note.get", new=AsyncMock(return_value=note)),
            patch.object(Note, "save", new=AsyncMock(return_value=None)),
            patch(
                "open_notebook.ai.models.model_manager.get_embedding_model",
                new=AsyncMock(return_value=object()),
            ),
        ):
            response = client.post(
                "/api/embed",
                json={"item_id": "note:abc123", "item_type": "note", "async_processing": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["command_id"] is None
