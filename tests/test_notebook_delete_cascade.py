"""Regression tests for #1124: notebook deletion must cascade to chat sessions.

Verifies that get_delete_preview() reports chat_session_count, that
delete() removes associated chat sessions and returns deleted_chat_sessions,
and — via integration tests against a real SurrealDB — that the cascade
logic in Notebook.delete() actually removes chat_session records and
refers_to edges from the database.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.database.repository import (
    db_connection,
    ensure_record_id,
    repo_query,
)
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# SurrealDB availability check (module-level, runs once)
# ---------------------------------------------------------------------------


def _probe_db_sync() -> bool:
    """Return True if SurrealDB is reachable (called once at import time)."""
    try:

        async def _probe():
            try:
                async with db_connection() as db:
                    await db.query("RETURN 1;")
                return True
            except Exception:
                return False

        return asyncio.run(_probe())
    except Exception:
        return False


_skip_if_no_db = pytest.mark.skipif(
    not _probe_db_sync(),
    reason="SurrealDB is not reachable — set SURREAL_URL / SURREAL_PASSWORD in .env",
)


# ---------------------------------------------------------------------------
# Serialization tests (existing — API response shape only)
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.mark.asyncio
@patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
async def test_delete_preview_includes_chat_session_count(mock_notebook_get, client):
    """delete-preview should return chat_session_count."""
    mock_notebook = MagicMock(spec=Notebook)
    mock_notebook.id = "notebook:test"
    mock_notebook.name = "Test"
    mock_notebook.get_delete_preview = AsyncMock(
        return_value={
            "note_count": 0,
            "exclusive_source_count": 0,
            "shared_source_count": 0,
            "chat_session_count": 3,
        }
    )
    mock_notebook_get.return_value = mock_notebook

    resp = client.get("/api/notebooks/notebook:test/delete-preview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["chat_session_count"] == 3
    assert data["note_count"] == 0
    assert data["exclusive_source_count"] == 0
    assert data["shared_source_count"] == 0


@pytest.mark.asyncio
@patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
async def test_delete_notebook_returns_deleted_chat_sessions(mock_notebook_get, client):
    """DELETE notebook should return deleted_chat_sessions in the response."""
    mock_notebook = MagicMock(spec=Notebook)
    mock_notebook.id = "notebook:test"
    mock_notebook.delete = AsyncMock(
        return_value={
            "deleted_notes": 0,
            "deleted_sources": 0,
            "unlinked_sources": 0,
            "deleted_chat_sessions": 2,
        }
    )
    mock_notebook_get.return_value = mock_notebook

    resp = client.delete("/api/notebooks/notebook:test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_chat_sessions"] == 2
    assert data["deleted_notes"] == 0
    assert data["unlinked_sources"] == 0


# ===========================================================================
# Integration test (exercises the actual cascade against SurrealDB)
# ===========================================================================


async def _cleanup_records(records: list[tuple[str, str | None]]) -> None:
    """Best-effort teardown: remove any surviving records and their edges."""
    for kind, rid in reversed(records):
        if rid is None:
            continue
        try:
            if kind == "notebook":
                try:
                    nb = await Notebook.get(rid)
                    await nb.delete(delete_exclusive_sources=True)
                except NotFoundError:
                    pass
            else:
                try:
                    obj = await ChatSession.get(rid)
                    await obj.delete()
                except NotFoundError:
                    pass

            for edge_table in ("refers_to", "reference", "artifact"):
                try:
                    await repo_query(
                        f"DELETE {edge_table} WHERE out = $rid OR in = $rid",
                        {"rid": ensure_record_id(rid)},
                    )
                except Exception:
                    pass
        except Exception:
            pass


@pytest.mark.asyncio
@_skip_if_no_db
async def test_notebook_delete_cascades_to_chat_sessions():
    """Real database cascade test for #1124.

    Creates a notebook and a chat session linked via ``refers_to``, then
    deletes the notebook and verifies:

    (a) ``get_delete_preview()`` reported the correct ``chat_session_count``
    (b) ``delete()`` returned the correct ``deleted_chat_sessions`` count
    (c) the ``chat_session`` record is removed from the database
    (d) the ``refers_to`` edge is removed from the database
    """
    created: list[tuple[str, str | None]] = []

    try:
        # ---- Arrange -------------------------------------------------------
        notebook = Notebook(
            name="Cascade Integration Test", description="regression for #1124"
        )
        await notebook.save()
        assert notebook.id is not None, "Notebook should have an id after save"
        notebook_id: str = notebook.id
        created.append(("notebook", notebook_id))

        session = ChatSession(title="Cascade Test Session")
        await session.save()
        assert session.id is not None, "ChatSession should have an id after save"
        session_id: str = session.id
        created.append(("chat_session", session_id))

        await session.relate_to_notebook(notebook_id)

        # ---- Assert — preview reports the session --------------------------
        preview = await notebook.get_delete_preview()
        expected_count = 1
        assert (
            preview["chat_session_count"] == expected_count
        ), (
            f"Expected {expected_count} session in preview, "
            f"got {preview['chat_session_count']}"
        )

        # ---- Act -----------------------------------------------------------
        result = await notebook.delete()

        # ---- Assert — deleted_chat_sessions count --------------------------
        assert result["deleted_chat_sessions"] == expected_count, (
            f"Expected {expected_count} deleted session, "
            f"got {result['deleted_chat_sessions']}"
        )

        # Notebook is gone — dont let cleanup retry it.
        created = [(k, v) for k, v in created if v != notebook_id]

        # ---- Assert — chat session record is gone --------------------------
        with pytest.raises(NotFoundError):
            await ChatSession.get(session_id)

        # Session is gone too.
        created = [(k, v) for k, v in created if v != session_id]

        # ---- Assert — refers_to edge is gone -------------------------------
        edges = await repo_query(
            "SELECT * FROM refers_to WHERE out = $id OR in = $id",
            {"id": ensure_record_id(notebook_id)},
        )
        assert edges == [], f"Expected zero refers_to edges, got {len(edges)}"

    finally:
        await _cleanup_records(created)
