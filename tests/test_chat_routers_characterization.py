"""Characterization tests for the chat and source-chat routers.

These pin down the behaviors shared (via copy-paste) between
`api/routers/chat.py` and `api/routers/source_chat.py` before/after extracting
them into `api/routers/_chat_shared.py`:

- record-ID normalization (bare id vs already-prefixed id)
- session/source verification (missing record -> 404, missing `refers_to`
  relation -> current behavior, preserved as-is)
- LangGraph state -> `ChatMessage` extraction shapes (type/content fallbacks)

DB access and LangGraph state are mocked following the style of
tests/test_crud_404.py.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _nf(*_args, **_kwargs):
    raise NotFoundError("not found")


def _session(**overrides):
    """A ChatSession-like object with the attributes the routers read."""
    defaults = dict(
        id="chat_session:abc",
        title="My Session",
        created="2026-01-01T00:00:00",
        updated="2026-01-02T00:00:00",
        model_override=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _source(**overrides):
    defaults = dict(id="source:xyz", title="My Source")
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _graph_state(values):
    state = MagicMock()
    state.values = values
    return state


class _Msg:
    """A LangChain-like message with id/type/content."""

    def __init__(self, id, type, content):
        self.id = id
        self.type = type
        self.content = content


class _Bare:
    """An object with no type/content attributes (exercises the fallbacks)."""

    def __str__(self):
        return "bare-repr"


# --- chat.py: ID normalization ------------------------------------------------


@pytest.mark.asyncio
@patch("api.routers.chat.repo_query", new_callable=AsyncMock)
@patch("api.routers.chat.chat_graph")
@patch("api.routers.chat.ChatSession.get", new_callable=AsyncMock)
async def test_get_chat_session_bare_id_gets_prefixed(
    mock_get, mock_graph, mock_repo, client
):
    mock_get.return_value = _session()
    mock_graph.get_state.return_value = _graph_state({"messages": []})
    mock_repo.return_value = [{"out": "notebook:1"}]

    resp = client.get("/api/chat/sessions/abc")

    assert resp.status_code == 200
    mock_get.assert_awaited_once_with("chat_session:abc")


@pytest.mark.asyncio
@patch("api.routers.chat.repo_query", new_callable=AsyncMock)
@patch("api.routers.chat.chat_graph")
@patch("api.routers.chat.ChatSession.get", new_callable=AsyncMock)
async def test_get_chat_session_prefixed_id_kept_as_is(
    mock_get, mock_graph, mock_repo, client
):
    mock_get.return_value = _session()
    mock_graph.get_state.return_value = _graph_state({"messages": []})
    mock_repo.return_value = [{"out": "notebook:1"}]

    resp = client.get("/api/chat/sessions/chat_session:abc")

    assert resp.status_code == 200
    mock_get.assert_awaited_once_with("chat_session:abc")


@pytest.mark.asyncio
@patch("api.routers.chat.ChatSession.get", new_callable=AsyncMock)
async def test_delete_chat_session_missing_returns_404(mock_get, client):
    mock_get.side_effect = _nf
    resp = client.delete("/api/chat/sessions/gone")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"
    mock_get.assert_awaited_once_with("chat_session:gone")


# --- chat.py: message extraction shape ----------------------------------------


@pytest.mark.asyncio
@patch("api.routers.chat.repo_query", new_callable=AsyncMock)
@patch("api.routers.chat.chat_graph")
@patch("api.routers.chat.ChatSession.get", new_callable=AsyncMock)
async def test_get_chat_session_message_shapes(mock_get, mock_graph, mock_repo, client):
    mock_get.return_value = _session()
    mock_graph.get_state.return_value = _graph_state(
        {"messages": [_Msg("m1", "human", "hello"), _Msg("m2", "ai", "hi"), _Bare()]}
    )
    mock_repo.return_value = [{"out": "notebook:1"}]

    resp = client.get("/api/chat/sessions/abc")

    assert resp.status_code == 200
    body = resp.json()
    assert body["message_count"] == 3
    assert body["messages"][0] == {
        "id": "m1",
        "type": "human",
        "content": "hello",
        "timestamp": None,
    }
    assert body["messages"][1]["type"] == "ai"
    # Object without type/content falls back to "unknown" / str(msg); the id
    # fallback is positional (msg_<index>).
    assert body["messages"][2] == {
        "id": "msg_2",
        "type": "unknown",
        "content": "bare-repr",
        "timestamp": None,
    }


@pytest.mark.asyncio
@patch("api.routers.chat.repo_query", new_callable=AsyncMock)
@patch("api.routers.chat.chat_graph")
@patch("api.routers.chat.ChatSession.get", new_callable=AsyncMock)
async def test_get_chat_session_no_state_yields_empty_messages(
    mock_get, mock_graph, mock_repo, client
):
    mock_get.return_value = _session()
    mock_graph.get_state.return_value = None
    mock_repo.return_value = []

    resp = client.get("/api/chat/sessions/abc")

    assert resp.status_code == 200
    body = resp.json()
    assert body["messages"] == []
    assert body["message_count"] == 0
    assert body["notebook_id"] is None


# --- source_chat.py: source verification --------------------------------------


@pytest.mark.asyncio
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_create_source_chat_session_missing_source_returns_404(mock_get, client):
    mock_get.side_effect = _nf
    resp = client.post(
        "/api/sources/gone/chat/sessions", json={"source_id": "gone"}
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source not found"
    mock_get.assert_awaited_once_with("source:gone")


@pytest.mark.asyncio
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_list_source_chat_sessions_missing_source_returns_404(mock_get, client):
    mock_get.side_effect = _nf
    resp = client.get("/api/sources/source:gone/chat/sessions")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source not found"
    mock_get.assert_awaited_once_with("source:gone")


# --- source_chat.py: session + relation verification ---------------------------


@pytest.mark.asyncio
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_get_source_chat_session_missing_session_returns_404(
    mock_source_get, mock_session_get, mock_repo, client
):
    mock_source_get.return_value = _source()
    mock_session_get.side_effect = _nf

    resp = client.get("/api/sources/xyz/chat/sessions/gone")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Source or session not found"
    mock_source_get.assert_awaited_once_with("source:xyz")
    mock_session_get.assert_awaited_once_with("chat_session:gone")


@pytest.mark.asyncio
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_get_source_chat_session_missing_relation_behavior(
    mock_source_get, mock_session_get, mock_repo, client
):
    """Session exists but is not related to the source.

    Current behavior (preserved as-is): the inner HTTPException(404) is
    swallowed by the broad `except Exception` and re-raised as a 500 whose
    detail embeds the original 404 message.
    """
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = []  # no refers_to relation

    resp = client.get("/api/sources/xyz/chat/sessions/abc")

    assert resp.status_code == 500
    assert (
        resp.json()["detail"]
        == "Error fetching source chat session: 404: Session not found for this source"
    )


@pytest.mark.asyncio
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_delete_source_chat_session_missing_relation_behavior(
    mock_source_get, mock_session_get, mock_repo, client
):
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = []

    resp = client.delete("/api/sources/xyz/chat/sessions/abc")

    assert resp.status_code == 500
    assert (
        resp.json()["detail"]
        == "Error deleting source chat session: 404: Session not found for this source"
    )


@pytest.mark.asyncio
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_send_message_missing_relation_returns_404(
    mock_source_get, mock_session_get, mock_repo, client
):
    """send_message re-raises HTTPException before its broad handler, so the
    missing-relation case surfaces as a real 404 here (unlike get/put/delete)."""
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = []

    resp = client.post(
        "/api/sources/xyz/chat/sessions/abc/messages", json={"message": "hi"}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found for this source"


@pytest.mark.asyncio
@patch("api.routers.source_chat.source_chat_graph")
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_get_source_chat_session_happy_path_shapes(
    mock_source_get, mock_session_get, mock_repo, mock_graph, client
):
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = [{"in": "chat_session:abc", "out": "source:xyz"}]
    mock_graph.get_state.return_value = _graph_state(
        {
            "messages": [_Msg("m1", "human", "hello"), _Bare()],
            "context_indicators": {"sources": ["source:xyz"], "insights": []},
        }
    )

    resp = client.get("/api/sources/xyz/chat/sessions/abc")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "chat_session:abc"
    assert body["source_id"] == "xyz"
    assert body["message_count"] == 2
    assert body["messages"][0] == {
        "id": "m1",
        "type": "human",
        "content": "hello",
        "timestamp": None,
    }
    assert body["messages"][1] == {
        "id": "msg_1",
        "type": "unknown",
        "content": "bare-repr",
        "timestamp": None,
    }
    assert body["context_indicators"] == {
        "sources": ["source:xyz"],
        "insights": [],
        "notes": [],
    }
