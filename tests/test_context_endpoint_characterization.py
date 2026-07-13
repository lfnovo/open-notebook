"""Characterization tests for POST /api/chat/context.

These pin down the exact response shape and the string-matching config
semantics ("not in" skips, "insights" -> short context, "full content" ->
long context) before the context-building loop is extracted out of the
router into open_notebook/utils/context_builder.py. They must pass
unchanged before and after the refactor.

DB access is mocked following the style of
tests/test_chat_routers_characterization.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _notebook(**overrides):
    defaults = dict(id="notebook:1", name="My Notebook")
    defaults.update(overrides)
    nb = SimpleNamespace(**defaults)
    nb.get_sources = AsyncMock(return_value=[])
    nb.get_notes = AsyncMock(return_value=[])
    return nb


def _source(source_id="source:s1", context=None):
    src = SimpleNamespace(id=source_id)
    src.get_context = AsyncMock(
        return_value=context if context is not None else {"id": source_id, "title": "T"}
    )
    return src


def _note(note_id="note:n1", context=None):
    note = SimpleNamespace(id=note_id)
    # Note.get_context is synchronous in the router code.
    note.get_context = MagicMock(
        return_value=context if context is not None else {"id": note_id, "title": "N"}
    )
    return note


# Patch the domain classes at their definition site so the tests are
# independent of which module hosts the context-building loop.
PATCH_NOTEBOOK = "open_notebook.domain.notebook.Notebook.get"
PATCH_SOURCE = "open_notebook.domain.notebook.Source.get"
PATCH_NOTE = "open_notebook.domain.notebook.Note.get"
PATCH_INSIGHTS = "open_notebook.domain.notebook.SourceInsight.get_for_sources"


@pytest.mark.asyncio
async def test_config_string_matching_semantics(client):
    """'not in' skips, 'insights' -> short, 'full content' -> long."""
    source_short = _source("source:s2", {"id": "source:s2", "insights": ["i"]})
    source_long = _source("source:s3", {"id": "source:s3", "full_text": "body"})
    note_full = _note("note:n2", {"id": "note:n2", "content": "note body"})

    async def get_source(full_id):
        return {"source:s2": source_short, "source:s3": source_long}[full_id]

    with (
        patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=_notebook())),
        patch(PATCH_SOURCE, new=AsyncMock(side_effect=get_source)),
        patch(PATCH_NOTE, new=AsyncMock(return_value=note_full)),
    ):
        response = client.post(
            "/api/chat/context",
            json={
                "notebook_id": "notebook:1",
                "context_config": {
                    "sources": {
                        "s1": "not in context",
                        "s2": "insights",
                        "s3": "full content",
                    },
                    "notes": {"n1": "not in context", "n2": "full content"},
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["sources"] == [
        {"id": "source:s2", "insights": ["i"]},
        {"id": "source:s3", "full_text": "body"},
    ]
    assert body["context"]["notes"] == [{"id": "note:n2", "content": "note body"}]

    # "insights" -> short context, "full content" -> long context
    source_short.get_context.assert_awaited_once_with(context_size="short")
    source_long.get_context.assert_awaited_once_with(context_size="long")
    note_full.get_context.assert_called_once_with(context_size="long")

    # char_count is the length of the concatenated str() of every context dict
    expected_content = (
        str({"id": "source:s2", "insights": ["i"]})
        + str({"id": "source:s3", "full_text": "body"})
        + str({"id": "note:n2", "content": "note body"})
    )
    assert body["char_count"] == len(expected_content)
    assert isinstance(body["token_count"], int)
    assert body["token_count"] > 0


@pytest.mark.asyncio
async def test_config_bare_ids_get_table_prefix(client):
    """Bare ids are prefixed with 'source:' / 'note:' before lookup."""
    source_get = AsyncMock(return_value=_source())
    note_get = AsyncMock(return_value=_note())

    with (
        patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=_notebook())),
        patch(PATCH_SOURCE, new=source_get),
        patch(PATCH_NOTE, new=note_get),
    ):
        response = client.post(
            "/api/chat/context",
            json={
                "notebook_id": "notebook:1",
                "context_config": {
                    "sources": {"abc": "insights"},
                    "notes": {"def": "full content"},
                },
            },
        )

    assert response.status_code == 200
    source_get.assert_awaited_once_with("source:abc")
    note_get.assert_awaited_once_with("note:def")


@pytest.mark.asyncio
async def test_config_missing_source_is_skipped(client):
    """A source lookup failure skips that source, not the whole request."""
    ok_source = _source("source:ok")

    async def get_source(full_id):
        if full_id == "source:missing":
            raise Exception("not found")
        return ok_source

    with (
        patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=_notebook())),
        patch(PATCH_SOURCE, new=AsyncMock(side_effect=get_source)),
    ):
        response = client.post(
            "/api/chat/context",
            json={
                "notebook_id": "notebook:1",
                "context_config": {
                    "sources": {"missing": "insights", "ok": "insights"},
                    "notes": {},
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["context"]["sources"] == [{"id": "source:ok", "title": "T"}]


@pytest.mark.asyncio
async def test_empty_config_defaults_to_all_short_contexts(client):
    """Falsy context_config -> every source (batched insights) and note, short."""
    src = _source("source:s1", {"id": "source:s1", "title": "S"})
    note = _note("note:n1", {"id": "note:n1", "title": "N"})
    notebook = _notebook()
    notebook.get_sources = AsyncMock(return_value=[src])
    notebook.get_notes = AsyncMock(return_value=[note])
    insights = [SimpleNamespace(id="source_insight:1")]

    with (
        patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=notebook)),
        patch(
            PATCH_INSIGHTS,
            new=AsyncMock(return_value={"source:s1": insights}),
        ),
    ):
        response = client.post(
            "/api/chat/context",
            json={"notebook_id": "notebook:1", "context_config": {}},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["context"]["sources"] == [{"id": "source:s1", "title": "S"}]
    assert body["context"]["notes"] == [{"id": "note:n1", "title": "N"}]
    src.get_context.assert_awaited_once_with(context_size="short", insights=insights)
    note.get_context.assert_called_once_with(context_size="short")


@pytest.mark.asyncio
async def test_default_path_survives_insight_batch_failure(client):
    """A failure batch-fetching insights falls back to empty insights."""
    src = _source("source:s1")
    notebook = _notebook()
    notebook.get_sources = AsyncMock(return_value=[src])

    with (
        patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=notebook)),
        patch(PATCH_INSIGHTS, new=AsyncMock(side_effect=Exception("db hiccup"))),
    ):
        response = client.post(
            "/api/chat/context",
            json={"notebook_id": "notebook:1", "context_config": {}},
        )

    assert response.status_code == 200
    src.get_context.assert_awaited_once_with(context_size="short", insights=[])


@pytest.mark.asyncio
async def test_missing_notebook_returns_404(client):
    with patch(PATCH_NOTEBOOK, new=AsyncMock(return_value=None)):
        response = client.post(
            "/api/chat/context",
            json={"notebook_id": "notebook:missing", "context_config": {}},
        )

    assert response.status_code == 404
