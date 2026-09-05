"""Characterization tests for the chat and source-chat routers.

These pin down the behaviors shared (via copy-paste) between
`api/routers/chat.py` and `api/routers/source_chat.py` before/after extracting
them into `api/routers/_chat_shared.py`:

- record-ID normalization (bare id vs already-prefixed id)
- session/source verification (missing record -> 404, missing `refers_to`
  relation -> 404 on every method now that the routers re-raise HTTPException
  instead of swallowing it into a 500)
- LangGraph state -> `ChatMessage` extraction shapes (type/content fallbacks)

DB access and LangGraph state are mocked following the style of
tests/test_crud_404.py.
"""

import asyncio
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

    Intentional behavior change: the router now re-raises HTTPException before
    its broad `except Exception`, so the inner 404 surfaces as a real 404
    instead of being swallowed and re-raised as a 500 embedding the original
    404 message.
    """
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = []  # no refers_to relation

    resp = client.get("/api/sources/xyz/chat/sessions/abc")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found for this source"


@pytest.mark.asyncio
@patch("api.routers._chat_shared.repo_query", new_callable=AsyncMock)
@patch("api.routers._chat_shared.ChatSession.get", new_callable=AsyncMock)
@patch("api.routers._chat_shared.Source.get", new_callable=AsyncMock)
async def test_delete_source_chat_session_missing_relation_behavior(
    mock_source_get, mock_session_get, mock_repo, client
):
    # Intentional behavior change: the inner 404 is no longer swallowed into a
    # 500 by the broad `except Exception` (see the get test above).
    mock_source_get.return_value = _source()
    mock_session_get.return_value = _session()
    mock_repo.return_value = []

    resp = client.delete("/api/sources/xyz/chat/sessions/abc")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found for this source"


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


# --- source_chat.py: SSE keepalive --------------------------------------------


@pytest.mark.asyncio
async def test_stream_source_chat_emits_keepalive_while_invoke_runs():
    """While the model generates, the generator yields an SSE comment so the
    connection never goes idle (proxies may otherwise drop it).

    The fake graph awaits an Event the test releases, so at least one keepalive
    timeout is guaranteed to fire — no wall-clock timing dependency."""
    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    release = asyncio.Event()

    async def controlled_ainvoke(*_args, **_kwargs):
        await release.wait()
        return {"messages": []}

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke.side_effect = controlled_ainvoke

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        gen = stream_source_chat_response(
            request, "chat_session:abc", "source:xyz", "hello"
        )

        # First event is the user message.
        first = await gen.__anext__()
        assert first.startswith('data: {"type": "user_message"')

        # The graph is still blocked on `release`, so the next event must be a
        # keepalive comment, not the AI message or completion.
        second = await gen.__anext__()
        assert second == ": ping\n\n"

        # Let generation finish and drain the remaining events.
        release.set()
        chunks = [chunk async for chunk in gen]

    assert chunks[-1].startswith('data: {"type": "complete"')


@pytest.mark.asyncio
async def test_stream_source_chat_cancels_invoke_on_disconnect():
    """When the client disconnects mid-generation, generation is cancelled
    server-side and the stream ends without a completion event."""
    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    cancelled = asyncio.Event()

    async def blocking_ainvoke(*_args, **_kwargs):
        try:
            await asyncio.Event().wait()  # blocks until cancelled
        except asyncio.CancelledError:
            cancelled.set()
            raise

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke.side_effect = blocking_ainvoke

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=True)

        chunks = []
        async for chunk in stream_source_chat_response(
            request, "chat_session:abc", "source:xyz", "hello"
        ):
            chunks.append(chunk)

    # The user message is still yielded up front, but the stream stops without
    # a completion event and the in-flight invoke task was cancelled.
    assert chunks[0].startswith('data: {"type": "user_message"')
    assert not any(c.startswith('data: {"type": "complete"') for c in chunks)
    assert cancelled.is_set()


# --- source_chat.py: duplicate user message on retry ---------------------------


@pytest.mark.asyncio
async def test_stream_source_chat_skips_duplicate_pending_user_message():
    """A retry after a failed generation must not append the user message twice.

    When the checkpoint already ends with a human turn carrying the same client
    `message_id` (an unanswered turn the frontend is retrying), the router skips
    the up-front `aupdate_state`. A completed exchange always ends with an AI
    message, so a trailing human turn is necessarily still pending.
    """
    from langchain_core.messages import HumanMessage

    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.get_state.return_value = _graph_state(
            {"messages": [HumanMessage(content="hello", id="msg-1")]}
        )
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={"messages": []})

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        chunks = []
        async for chunk in stream_source_chat_response(
            request, "chat_session:abc", "source:xyz", "hello", message_id="msg-1"
        ):
            chunks.append(chunk)

    # The duplicate pending user message is NOT re-appended.
    mock_graph.aupdate_state.assert_not_awaited()
    assert chunks[0].startswith('data: {"type": "user_message"')
    assert chunks[-1].startswith('data: {"type": "complete"')


@pytest.mark.asyncio
async def test_stream_source_chat_appends_user_message_when_not_pending():
    """When the checkpoint ends with an AI message (a completed exchange), the
    new user message IS appended up front, carrying the client message_id."""
    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.get_state.return_value = _graph_state(
            {"messages": [_Msg("m1", "human", "hi"), _Msg("m2", "ai", "yo")]}
        )
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={"messages": []})

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        chunks = []
        async for chunk in stream_source_chat_response(
            request, "chat_session:abc", "source:xyz", "hello", message_id="msg-new"
        ):
            chunks.append(chunk)

    mock_graph.aupdate_state.assert_awaited_once()
    _, payload = mock_graph.aupdate_state.await_args.args
    assert payload["messages"][0].content == "hello"
    assert payload["messages"][0].id == "msg-new"
    assert chunks[0].startswith('data: {"type": "user_message"')
    assert chunks[-1].startswith('data: {"type": "complete"')


@pytest.mark.asyncio
async def test_stream_source_chat_appends_distinct_identical_messages():
    """Two distinct identical messages (same content, different message_id) are
    both appended — dedup keys on identity, not content.

    A trailing human turn with a *different* id is not the same retry, so the
    new message must be persisted rather than silently dropped."""
    from langchain_core.messages import HumanMessage

    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.get_state.return_value = _graph_state(
            {"messages": [HumanMessage(content="hello", id="msg-1")]}
        )
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={"messages": []})

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        chunks = []
        async for chunk in stream_source_chat_response(
            request, "chat_session:abc", "source:xyz", "hello", message_id="msg-2"
        ):
            chunks.append(chunk)

    # Same content but a different id -> still appended, not deduplicated.
    mock_graph.aupdate_state.assert_awaited_once()
    _, payload = mock_graph.aupdate_state.await_args.args
    assert payload["messages"][0].content == "hello"
    assert payload["messages"][0].id == "msg-2"
    assert chunks[0].startswith('data: {"type": "user_message"')
    assert chunks[-1].startswith('data: {"type": "complete"')


@pytest.mark.asyncio
async def test_stream_source_chat_evicts_session_lock_after_stream():
    """The per-session lock entry is evicted once the stream finishes, so a
    long-lived process does not retain one lock per session it has ever seen."""
    from api.routers import source_chat as source_chat_router
    from api.routers.source_chat import stream_source_chat_response

    session_id = "chat_session:lock-evict"

    with patch.object(
        source_chat_router, "KEEPALIVE_INTERVAL_SECONDS", 0.01
    ), patch.object(source_chat_router, "source_chat_graph") as mock_graph:
        mock_graph.get_state.return_value = _graph_state({"messages": []})
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={"messages": []})

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        async for _chunk in stream_source_chat_response(
            request, session_id, "source:xyz", "hello"
        ):
            pass

    assert session_id not in source_chat_router._session_locks
