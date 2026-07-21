"""Characterization: one full notebook create/read/update/delete cycle.

Captures the CURRENT behavior of the notebook lifecycle as of `upstream-base`.
See ./README.md before changing anything here.

Mocked at the domain/repository boundary so the real routers, request parsing
and response models run without a live SurrealDB.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _notebook_row(
    notebook_id="notebook:abc",
    name="My notebook",
    description="A description",
    archived=False,
    source_count=3,
    note_count=2,
):
    """A row shaped like the SELECT ... count(...) query the router runs."""
    return {
        "id": notebook_id,
        "name": name,
        "description": description,
        "archived": archived,
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-01-02T00:00:00Z",
        "source_count": source_count,
        "note_count": note_count,
    }


class TestCreate:
    """POST /api/notebooks"""

    def test_create_returns_200_with_zero_counts(self, client):
        """A freshly created notebook reports source_count/note_count as 0.

        Note the status code is 200, not 201 — FastAPI's default. Captured as-is.
        """
        saved = []

        async def capture_save(self_nb):
            saved.append(self_nb)
            self_nb.id = "notebook:new"

        with patch.object(Notebook, "save", autospec=True, side_effect=capture_save):
            response = client.post(
                "/api/notebooks",
                json={"name": "My notebook", "description": "A description"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "notebook:new"
        assert body["name"] == "My notebook"
        assert body["description"] == "A description"
        assert body["archived"] is False
        # Hard-coded to 0 by the router, not queried.
        assert body["source_count"] == 0
        assert body["note_count"] == 0

        assert len(saved) == 1
        assert saved[0].name == "My notebook"

    def test_create_with_blank_name_returns_400(self, client):
        """The `name_must_not_be_empty` validator raises InvalidInputError -> 400.

        Note this is a 400, not the 422 a plain pydantic validation error would
        give, because the validator raises a domain exception.
        """
        response = client.post(
            "/api/notebooks", json={"name": "   ", "description": "x"}
        )
        assert response.status_code == 400

    def test_create_without_description_defaults_to_empty_string(self, client):
        """`description` is optional on the API model (defaults to "") even though
        the domain model types it as a required str."""

        async def capture_save(self_nb):
            self_nb.id = "notebook:new"

        with patch.object(Notebook, "save", autospec=True, side_effect=capture_save):
            response = client.post("/api/notebooks", json={"name": "Only a name"})

        assert response.status_code == 200
        assert response.json()["description"] == ""

    def test_create_missing_name_returns_422(self, client):
        """`name` has no default — omitting it is a plain pydantic 422."""
        response = client.post("/api/notebooks", json={"description": "no name"})
        assert response.status_code == 422


class TestRead:
    """GET /api/notebooks and GET /api/notebooks/{id}"""

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_get_one_returns_counts_from_query(self, mock_query, client):
        # First call = the SELECT; second = the best-effort last_viewed_at stamp.
        mock_query.side_effect = [[_notebook_row()], []]

        response = client.get("/api/notebooks/notebook:abc")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "notebook:abc"
        assert body["source_count"] == 3
        assert body["note_count"] == 2

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_get_one_missing_returns_404(self, mock_query, client):
        mock_query.return_value = []
        response = client.get("/api/notebooks/notebook:nope")
        assert response.status_code == 404
        assert response.json()["detail"] == "Notebook not found"

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_get_one_still_200_when_view_stamp_fails(self, mock_query, client):
        """Recording last_viewed_at is best-effort: its failure must not 500."""
        mock_query.side_effect = [[_notebook_row()], RuntimeError("stamp blew up")]

        response = client.get("/api/notebooks/notebook:abc")

        assert response.status_code == 200

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_list_returns_all(self, mock_query, client):
        mock_query.return_value = [
            _notebook_row(notebook_id="notebook:1", name="One"),
            _notebook_row(notebook_id="notebook:2", name="Two"),
        ]

        response = client.get("/api/notebooks")

        assert response.status_code == 200
        assert [nb["name"] for nb in response.json()] == ["One", "Two"]

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_list_archived_filter_is_applied_in_python(self, mock_query, client):
        """`archived` filters the already-fetched rows, it is not pushed into SQL."""
        mock_query.return_value = [
            _notebook_row(notebook_id="notebook:1", name="Active", archived=False),
            _notebook_row(notebook_id="notebook:2", name="Archived", archived=True),
        ]

        response = client.get("/api/notebooks?archived=true")

        assert response.status_code == 200
        assert [nb["name"] for nb in response.json()] == ["Archived"]

    @pytest.mark.parametrize(
        "order_by",
        ["name", "name asc", "created desc", "updated desc"],
    )
    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_allowed_order_by_accepted(self, mock_query, order_by, client):
        mock_query.return_value = []
        response = client.get("/api/notebooks", params={"order_by": order_by})
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "order_by",
        ["id", "name; DROP TABLE notebook", "name sideways", "name asc desc"],
    )
    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    def test_disallowed_order_by_returns_400(self, mock_query, order_by, client):
        """order_by is allowlisted (SurrealQL injection guard) — rejected with 400."""
        mock_query.return_value = []
        response = client.get("/api/notebooks", params={"order_by": order_by})
        assert response.status_code == 400


class TestUpdate:
    """PUT /api/notebooks/{id}"""

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_update_applies_only_provided_fields(self, mock_get, mock_query, client):
        notebook = Notebook(name="Old name", description="Old description")
        notebook.id = "notebook:abc"
        mock_get.return_value = notebook
        mock_query.return_value = [
            _notebook_row(name="New name", description="Old description")
        ]

        with patch.object(Notebook, "save", new_callable=AsyncMock):
            response = client.put(
                "/api/notebooks/notebook:abc", json={"name": "New name"}
            )

        assert response.status_code == 200
        # description was omitted from the payload, so it is left untouched.
        assert notebook.name == "New name"
        assert notebook.description == "Old description"

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_update_can_archive(self, mock_get, mock_query, client):
        notebook = Notebook(name="N", description="D")
        notebook.id = "notebook:abc"
        mock_get.return_value = notebook
        mock_query.return_value = [_notebook_row(archived=True)]

        with patch.object(Notebook, "save", new_callable=AsyncMock):
            response = client.put(
                "/api/notebooks/notebook:abc", json={"archived": True}
            )

        assert response.status_code == 200
        assert response.json()["archived"] is True
        assert notebook.archived is True

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_update_falls_back_to_in_memory_state_when_reselect_is_empty(
        self, mock_get, mock_query, client
    ):
        """If the post-update SELECT returns nothing, the router still 200s using
        the in-memory notebook, reporting counts as 0."""
        notebook = Notebook(name="N", description="D")
        notebook.id = "notebook:abc"
        mock_get.return_value = notebook
        mock_query.return_value = []

        with patch.object(Notebook, "save", new_callable=AsyncMock):
            response = client.put(
                "/api/notebooks/notebook:abc", json={"name": "Renamed"}
            )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Renamed"
        assert body["source_count"] == 0
        assert body["note_count"] == 0

    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_update_missing_returns_404(self, mock_get, client):
        mock_get.side_effect = NotFoundError("no such notebook")
        response = client.put("/api/notebooks/notebook:nope", json={"name": "x"})
        assert response.status_code == 404


class TestDelete:
    """DELETE /api/notebooks/{id}"""

    @patch("api.routers.notebooks.Notebook.delete", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_delete_defaults_to_keeping_exclusive_sources(
        self, mock_get, mock_delete, client
    ):
        notebook = Notebook(name="N", description="D")
        notebook.id = "notebook:abc"
        mock_get.return_value = notebook
        mock_delete.return_value = {
            "deleted_notes": 2,
            "deleted_sources": 0,
            "unlinked_sources": 5,
            "deleted_chat_sessions": 1,
        }

        response = client.delete("/api/notebooks/notebook:abc")

        assert response.status_code == 200
        body = response.json()
        assert body["message"] == "Notebook deleted successfully"
        assert body["deleted_notes"] == 2
        assert body["unlinked_sources"] == 5
        # Default is False — sources are unlinked, not destroyed.
        mock_delete.assert_awaited_once_with(delete_exclusive_sources=False)

    @patch("api.routers.notebooks.Notebook.delete", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_delete_can_cascade_to_exclusive_sources(
        self, mock_get, mock_delete, client
    ):
        notebook = Notebook(name="N", description="D")
        notebook.id = "notebook:abc"
        mock_get.return_value = notebook
        mock_delete.return_value = {
            "deleted_notes": 2,
            "deleted_sources": 4,
            "unlinked_sources": 0,
            "deleted_chat_sessions": 1,
        }

        response = client.delete(
            "/api/notebooks/notebook:abc?delete_exclusive_sources=true"
        )

        assert response.status_code == 200
        assert response.json()["deleted_sources"] == 4
        mock_delete.assert_awaited_once_with(delete_exclusive_sources=True)

    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_delete_missing_returns_404(self, mock_get, client):
        mock_get.side_effect = NotFoundError("no such notebook")
        response = client.delete("/api/notebooks/notebook:nope")
        assert response.status_code == 404


class TestFullCycle:
    """create -> read -> update -> delete, in order, as one flow."""

    @patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
    @patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
    def test_full_lifecycle(self, mock_get, mock_query, client):
        # --- create ---
        async def capture_save(self_nb):
            self_nb.id = "notebook:cycle"

        with patch.object(Notebook, "save", autospec=True, side_effect=capture_save):
            created = client.post(
                "/api/notebooks",
                json={"name": "Cycle", "description": "lifecycle test"},
            )
        assert created.status_code == 200
        notebook_id = created.json()["id"]

        # --- read ---
        mock_query.side_effect = [
            [_notebook_row(notebook_id=notebook_id, name="Cycle")],
            [],
        ]
        read = client.get(f"/api/notebooks/{notebook_id}")
        assert read.status_code == 200
        assert read.json()["name"] == "Cycle"

        # --- update ---
        notebook = Notebook(name="Cycle", description="lifecycle test")
        notebook.id = notebook_id
        mock_get.return_value = notebook
        mock_query.side_effect = None
        mock_query.return_value = [
            _notebook_row(notebook_id=notebook_id, name="Cycle renamed")
        ]
        with patch.object(Notebook, "save", new_callable=AsyncMock):
            updated = client.put(
                f"/api/notebooks/{notebook_id}", json={"name": "Cycle renamed"}
            )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Cycle renamed"

        # --- delete ---
        with patch.object(
            Notebook,
            "delete",
            new_callable=AsyncMock,
            return_value={
                "deleted_notes": 0,
                "deleted_sources": 0,
                "unlinked_sources": 0,
                "deleted_chat_sessions": 0,
            },
        ):
            deleted = client.delete(f"/api/notebooks/{notebook_id}")

        assert deleted.status_code == 200
        assert deleted.json()["message"] == "Notebook deleted successfully"
