from unittest.mock import AsyncMock, MagicMock, call

import pytest
from surrealdb import RecordID

from open_notebook.database import repository


@pytest.fixture
def connection(monkeypatch):
    db = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=db)
    context.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=context)
    monkeypatch.setattr(repository, "db_connection", factory)
    return db, context, factory


@pytest.mark.asyncio
async def test_insert_batches_share_one_connection(connection):
    db, context, factory = connection
    records = [{"id": RecordID("source_embedding", str(i))} for i in range(120)]
    db.insert.side_effect = lambda table, batch: batch

    result = await repository.repo_insert("source_embedding", records)

    assert db.insert.await_args_list == [
        call("source_embedding", records[:50]),
        call("source_embedding", records[50:100]),
        call("source_embedding", records[100:]),
    ]
    assert result == [{"id": str(record["id"])} for record in records]
    factory.assert_called_once_with()
    context.__aenter__.assert_awaited_once()
    context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_insert_does_not_open_connection(connection):
    db, _, factory = connection
    assert await repository.repo_insert("source_embedding", []) == []
    factory.assert_not_called()
    db.insert.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [0, -1])
async def test_invalid_batch_size_does_not_open_connection(connection, batch_size):
    _, _, factory = connection
    with pytest.raises(ValueError, match="batch_size must be greater than zero"):
        await repository.repo_insert(
            "source_embedding", [{"content": "chunk"}], batch_size=batch_size
        )
    factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [RuntimeError("insert failed"), "insert failed"])
async def test_failed_batch_stops_and_closes_connection(connection, error):
    db, context, factory = connection
    records = [{"content": str(i)} for i in range(3)]
    db.insert.side_effect = [records[:1], error, records[2:]]

    with pytest.raises(RuntimeError, match="insert failed"):
        await repository.repo_insert("source_embedding", records, batch_size=1)

    assert db.insert.await_count == 2
    factory.assert_called_once_with()
    context.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_ignored_duplicate_batch_continues_on_same_connection(connection):
    db, context, factory = connection
    records = [{"content": str(i)} for i in range(3)]
    db.insert.side_effect = [
        records[:1],
        RuntimeError("already contains record"),
        records[2:],
    ]

    result = await repository.repo_insert(
        "source_embedding", records, ignore_duplicates=True, batch_size=1
    )

    assert result == [records[0], records[2]]
    assert db.insert.await_count == 3
    factory.assert_called_once_with()
    context.__aexit__.assert_awaited_once()
