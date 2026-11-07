"""A source delete must not answer 200 while embeddings remain (issue #1510).

SurrealDB transaction conflicts during the embeddings/insights cleanup used to
be logged, the uploaded file was removed anyway and the API still returned 200
OK with the source record and all its chunks still in place.

The database is faked here: the embeddings cleanup either fails with a
retriable conflict, a permanent error or succeeds.
"""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import Source
from open_notebook.exceptions import DatabaseOperationError


def _make_source(file_path):
    return Source(
        id="source:abc",
        title="test",
        full_text="content",
        asset={"file_path": file_path},
    )


@pytest.mark.asyncio
async def test_permanent_conflict_raises_and_keeps_file(tmp_path):
    """A persistent conflict during cleanup must surface as an error and leave
    the uploaded file in place for a later retry."""
    asset_file = tmp_path / "upload.pdf"
    asset_file.write_text("some bytes")

    source = _make_source(str(asset_file))

    with patch(
        "open_notebook.domain.notebook.repo_query",
        new=AsyncMock(
            side_effect=RuntimeError(
                "The query was not executed due to a failed transaction. "
                "Failed to commit transaction due to a read or write conflict. "
                "This transaction can be retried"
            )
        ),
    ):
        with pytest.raises(DatabaseOperationError, match="embeddings"):
            await source.delete()

    assert asset_file.exists(), "the uploaded file must outlive the failed delete"


@pytest.mark.asyncio
async def test_retryable_conflict_recovers(tmp_path):
    """A conflict that clears on retry lets the delete finish normally."""
    asset_file = tmp_path / "upload.pdf"
    asset_file.write_text("some bytes")

    source = _make_source(str(asset_file))

    calls = []

    async def flaky_repo_query(query, params=None):
        calls.append(query)
        if len(calls) <= 1:
            raise RuntimeError(
                "Failed to commit transaction due to a read or write conflict. "
                "This transaction can be retried"
            )
        return []

    source_delete = AsyncMock(return_value=None)

    with (
        patch(
            "open_notebook.domain.notebook.repo_query",
            new=AsyncMock(side_effect=flaky_repo_query),
        ),
        patch(
            "open_notebook.domain.base.ObjectModel.delete",
            new=source_delete,
        ),
    ):
        assert await source.delete() is None

    # The first failing call was retried, not silently swallowed.
    assert len(calls) >= 2
    assert source_delete.call_count == 1
    assert not asset_file.exists(), (
        "the uploaded file is removed only after the records are gone"
    )


@pytest.mark.asyncio
async def test_non_retryable_error_raises_immediately(tmp_path):
    """An error that is not a retriable aborts right away (single attempt)."""
    asset_file = tmp_path / "upload.pdf"
    asset_file.write_text("some bytes")

    source = _make_source(str(asset_file))

    mock_query = AsyncMock(side_effect=ConnectionError("websocket closed"))
    with (
        patch(
            "open_notebook.domain.notebook.repo_query",
            new=mock_query,
        ),
        patch("asyncio.sleep", new=AsyncMock()) as sleep_mock,
        pytest.raises(DatabaseOperationError, match="embeddings"),
    ):
        await source.delete()

    assert sleep_mock.call_count == 0, "non-retriable errors do not retry"
    assert mock_query.call_count == 1
    assert asset_file.exists()
