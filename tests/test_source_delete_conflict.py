"""DELETE /api/sources/{id} must not report success when the delete failed (#1510).

While the worker writes embeddings, SurrealDB can reject the delete with a
retryable transaction conflict. The delete is retried a few times; if it still
fails the API returns an error, and the uploaded file is kept.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.database import repository
from open_notebook.domain import notebook as notebook_module
from open_notebook.domain.notebook import Asset, Source
from open_notebook.exceptions import DatabaseOperationError

CONFLICT = (
    "The query was not executed due to a failed transaction. Failed to commit "
    "transaction due to a read or write conflict. This transaction can be retried"
)


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    # raising=False so the tests still run (and fail) against code without the retry
    monkeypatch.setattr(
        notebook_module, "SOURCE_DELETE_RETRY_DELAY_SECONDS", 0, raising=False
    )


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture
def source_file(tmp_path):
    path = tmp_path / "upload.pdf"
    path.write_bytes(b"pdf")
    return path


def _source(file_path=None):
    asset = Asset(file_path=str(file_path)) if file_path else None
    return Source(id="source:abc", title="Doc", asset=asset)


@pytest.mark.asyncio
async def test_conflict_then_success_retries_and_deletes_file(source_file):
    repo_query = AsyncMock(side_effect=[RuntimeError(CONFLICT), [], []])
    repo_delete = AsyncMock(return_value={"id": "source:abc"})

    with (
        patch("open_notebook.domain.notebook.repo_query", repo_query),
        patch("open_notebook.domain.base.repo_delete", repo_delete),
    ):
        assert await _source(source_file).delete()

    assert repo_query.await_count == 3
    repo_delete.assert_awaited_once()
    assert not source_file.exists()


@pytest.mark.asyncio
async def test_record_delete_conflict_is_retried():
    # repo_delete conflicts are wrapped by ObjectModel.delete() in a generic
    # DatabaseOperationError; the conflict must still be detected.
    repo_delete = AsyncMock(
        side_effect=[RuntimeError(f"Failed to delete record: {CONFLICT}"), None]
    )

    with (
        patch("open_notebook.domain.notebook.repo_query", AsyncMock(return_value=[])),
        patch("open_notebook.domain.base.repo_delete", repo_delete),
    ):
        await _source().delete()

    assert repo_delete.await_count == 2


@pytest.mark.asyncio
async def test_persistent_conflict_raises_and_keeps_file(source_file):
    repo_query = AsyncMock(side_effect=RuntimeError(CONFLICT))
    repo_delete = AsyncMock()

    with (
        patch("open_notebook.domain.notebook.repo_query", repo_query),
        patch("open_notebook.domain.base.repo_delete", repo_delete),
        pytest.raises(DatabaseOperationError, match="transaction conflict"),
    ):
        await _source(source_file).delete()

    assert repo_query.await_count == notebook_module.SOURCE_DELETE_MAX_ATTEMPTS
    repo_delete.assert_not_awaited()
    assert source_file.exists()


@pytest.mark.asyncio
async def test_persistent_record_delete_conflict_raises_and_keeps_file(source_file):
    # The embeddings and insights are gone, but the source record itself can't
    # be deleted: the file must stay so the source still points at it.
    repo_delete = AsyncMock(
        side_effect=RuntimeError(f"Failed to delete record: {CONFLICT}")
    )

    with (
        patch("open_notebook.domain.notebook.repo_query", AsyncMock(return_value=[])),
        patch("open_notebook.domain.base.repo_delete", repo_delete),
        pytest.raises(DatabaseOperationError, match="transaction conflict"),
    ):
        await _source(source_file).delete()

    assert repo_delete.await_count == notebook_module.SOURCE_DELETE_MAX_ATTEMPTS
    assert source_file.exists()


@pytest.mark.asyncio
async def test_notebook_delete_stops_when_an_exclusive_source_delete_fails():
    # Before, the failure was logged and the notebook delete went on: the
    # source was unlinked from every notebook but still existed.
    from open_notebook.domain.notebook import Notebook

    queries = []

    async def repo_query(query, params=None):
        queries.append(query)
        if "assigned_others" in query:
            return [{"id": "source:abc", "assigned_others": 0}]
        return []

    failing_source = AsyncMock()
    failing_source.delete.side_effect = DatabaseOperationError(
        "Failed to delete source: database transaction conflict, please retry"
    )
    notebook = Notebook(id="notebook:nb", name="NB", description="")

    with (
        patch("open_notebook.domain.notebook.repo_query", repo_query),
        patch.object(Notebook, "get_notes", AsyncMock(return_value=[])),
        patch.object(Source, "get", AsyncMock(return_value=failing_source)),
        patch("open_notebook.domain.base.repo_delete", AsyncMock()) as repo_delete,
        pytest.raises(DatabaseOperationError, match="Failed to delete notebook"),
    ):
        await notebook.delete(delete_exclusive_sources=True)

    assert not any(q.strip().startswith("DELETE reference") for q in queries)
    repo_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_errors_are_not_retried():
    repo_query = AsyncMock(side_effect=RuntimeError("connection refused"))

    with (
        patch("open_notebook.domain.notebook.repo_query", repo_query),
        pytest.raises(DatabaseOperationError, match="Failed to delete source"),
    ):
        await _source().delete()

    repo_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_repo_delete_raises_on_error_string(monkeypatch):
    # The SDK returns the error text instead of raising on a failed DELETE.
    db = AsyncMock()
    db.delete.return_value = CONFLICT
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(repository, "db_connection", lambda: context)

    with pytest.raises(DatabaseOperationError, match="can be retried"):
        await repository.repo_delete("source:abc")


def test_api_returns_200_after_retried_conflict(client):
    repo_query = AsyncMock(side_effect=[RuntimeError(CONFLICT), [], []])

    with (
        patch("api.routers.sources.Source.get", AsyncMock(return_value=_source())),
        patch("open_notebook.domain.notebook.repo_query", repo_query),
        patch("open_notebook.domain.base.repo_delete", AsyncMock(return_value=None)),
    ):
        response = client.delete("/api/sources/source:abc")

    assert response.status_code == 200
    assert repo_query.await_count == 3


def test_api_returns_error_when_delete_keeps_failing(client):
    with (
        patch("api.routers.sources.Source.get", AsyncMock(return_value=_source())),
        patch(
            "open_notebook.domain.notebook.repo_query",
            AsyncMock(side_effect=RuntimeError(CONFLICT)),
        ),
        patch("open_notebook.domain.base.repo_delete", AsyncMock()),
    ):
        response = client.delete("/api/sources/source:abc")

    assert response.status_code == 500
    assert "transaction conflict" in response.json()["detail"]
    assert "deleted successfully" not in response.text
