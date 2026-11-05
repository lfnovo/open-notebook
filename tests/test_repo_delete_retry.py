"""repo_delete must retry a retriable SurrealDB transaction conflict (#1510).

A delete racing with a concurrent embed write used to fail immediately with a
RuntimeError even though the conflict is explicitly retriable.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from surrealdb import RecordID

from open_notebook.database import repository

CONFLICT = (
    "Failed to commit transaction due to a read or write conflict. "
    "This transaction can be retried"
)


@pytest.fixture
def connection(monkeypatch):
    db = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=db)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(repository, "db_connection", MagicMock(return_value=context))
    monkeypatch.setattr(repository.asyncio, "sleep", AsyncMock())
    return db


@pytest.mark.asyncio
async def test_retries_conflict_then_succeeds(connection):
    connection.delete.side_effect = [RuntimeError(CONFLICT), "deleted-record"]

    result = await repository.repo_delete(RecordID.parse("source:abc"))

    assert result == "deleted-record"
    assert connection.delete.call_count == 2


@pytest.mark.asyncio
async def test_keeps_failing_conflict_bubbles_up(connection):
    connection.delete.side_effect = RuntimeError(CONFLICT)

    with pytest.raises(RuntimeError, match="Failed to delete record"):
        await repository.repo_delete("source:abc", max_attempts=2)

    assert connection.delete.call_count == 2


@pytest.mark.asyncio
async def test_non_retryable_error_fails_immediately(connection):
    connection.delete.side_effect = ConnectionError("websocket closed")

    with pytest.raises(RuntimeError, match="Failed to delete record"):
        await repository.repo_delete("source:abc")

    assert connection.delete.call_count == 1
