"""Regression tests for #1452: a malformed notebook id must be a 400, not a 500.

`GET /api/notebooks/abc123` (an id with no `notebook:` prefix) ran the path
segment through `ensure_record_id()`, which lets SurrealDB's
`RecordID.parse` ValueError escape. The router's catch-all
`except Exception` arm then turned a client-side formatting mistake into a 500
whose detail leaked a driver message
("invalid string provided for parse. the expected string format is
\"table_name:record_id\"").

The fix keeps the existing error convention instead of adding a new one: the
router raises `InvalidInputError`, the `except OpenNotebookError: raise` arm
re-raises it, and the global handler in api/main.py maps it to 400 — the same
route the sibling single-record endpoints take through the domain layer
(`ObjectModel.get` raises `InvalidInputError` for an id it cannot resolve).

DB access is mocked following the style of tests/test_crud_404.py and
tests/test_recently_viewed_api.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# The driver message that used to be returned to the client as a 500.
SURREALDB_PARSE_ERROR = "invalid string provided for parse"


@pytest.fixture
def client():
    from api.main import app

    # raise_server_exceptions=False so an exception that escapes the app shows
    # up as a 500 response instead of blowing up the test.
    return TestClient(app, raise_server_exceptions=False)


# --- the fix itself ------------------------------------------------------------


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_bare_id_returns_400(mock_repo_query, client):
    response = client.get("/api/notebooks/abc123")

    assert response.status_code == 400
    assert "notebook:" in response.json()["detail"]
    # The driver message is a 500's fingerprint; it must not reach the client.
    assert SURREALDB_PARSE_ERROR not in response.json()["detail"]


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_malformed_id_never_touches_the_database(mock_repo_query, client):
    """A rejected id is a client error: no query, and no last-viewed stamp."""
    response = client.get("/api/notebooks/abc123")

    assert response.status_code == 400
    mock_repo_query.assert_not_called()


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_malformed_id_returns_400(mock_repo_query, client):
    response = client.get("/api/notebooks/abc123")

    assert response.status_code == 400
    assert "notebook:" in response.json()["detail"]


# --- the 400 must not become a reflection channel --------------------------------


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_400_does_not_echo_the_id(mock_repo_query, client):
    """The id is what the caller just sent; repeating it back adds nothing.

    A notebook id is a bare record id such as `abc123`, so this is the input a
    stale bookmark or a hand-edited request produces -- the same one #1452 is
    about.
    """
    response = client.get("/api/notebooks/abc123")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "abc123" not in detail
    assert "notebook:<id>" in detail


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_prefixed_id_still_works(mock_repo_query, client):
    """The validation must not reject a well-formed id."""
    mock_repo_query.return_value = [
        {
            "id": "notebook:abc123",
            "name": "Research",
            "description": "",
            "archived": False,
            "created": "2026-01-01T00:00:00Z",
            "updated": "2026-01-02T00:00:00Z",
            "source_count": 2,
            "note_count": 5,
        }
    ]

    response = client.get("/api/notebooks/notebook:abc123")

    assert response.status_code == 200
    assert response.json()["id"] == "notebook:abc123"
    assert response.json()["source_count"] == 2
    # Read + best-effort last_viewed stamp, both with the parsed record id.
    assert mock_repo_query.await_count == 2
    for call in mock_repo_query.await_args_list:
        assert str(call.args[1]["notebook_id"]) == "notebook:abc123"


@patch("api.routers.notebooks.repo_query", new_callable=AsyncMock)
def test_get_notebook_missing_record_still_returns_404(mock_repo_query, client):
    mock_repo_query.return_value = []

    assert client.get("/api/notebooks/notebook:gone").status_code == 404


# --- consistency with the sibling single-record endpoints ----------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/notebooks/abc123",
        "/api/sources/abc123",
        "/api/notes/abc123",
        "/api/transformations/abc123",
    ],
)
def test_bare_id_is_a_client_error_on_every_single_record_endpoint(path, client):
    """#1452 is the inconsistency itself: notebooks answered 500 where its
    siblings answer 400. These endpoints must agree."""
    assert client.get(path).status_code == 400
