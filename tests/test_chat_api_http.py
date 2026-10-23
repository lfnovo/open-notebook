"""HTTP-level tests for the streaming and buffered chat endpoints.

The event-sequence tests in `test_chat_streaming.py` drive the response
generator directly. These go through FastAPI itself: status codes, SSE headers,
request validation and the guarantee that the buffered endpoint stays
non-streaming now that streaming endpoints ask for a streaming model.

DB and model calls are mocked in the style of the characterization tests.
"""

import json
import sqlite3
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _session(**overrides):
    defaults = dict(
        id="chat_session:abc",
        title="My Session",
        created="2026-01-01T00:00:00",
        updated="2026-01-02T00:00:00",
        model_override=None,
        save=AsyncMock(),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _graph_state(values):
    state = MagicMock()
    state.values = values
    return state


def _empty_state():
    def _state(*_args, **_kwargs):
        return _graph_state({"messages": []})

    return _state


class _Chunk:
    def __init__(self, content):
        self.content = content


class _FakeStreamingModel:
    async def astream(self, _payload):
        yield _Chunk("Hel")
        yield _Chunk("lo")


def _frames(text):
    return [
        json.loads(line[len("data: ") :])
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


@contextmanager
def _patched_stream(model):
    """Everything the streaming handler touches, besides HTTP itself."""
    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch(
            "api.routers.chat.provision_langchain_model",
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            "api.routers.chat.get_session_or_404",
            new_callable=AsyncMock,
            return_value=("chat_session:abc", _session()),
        ),
        patch("api.routers.chat.repo_query", new_callable=AsyncMock, return_value=[]),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=MagicMock()),
    ):
        yield graph


def _post_stream(client, body=None):
    body = (
        body
        if body is not None
        else {
            "session_id": "chat_session:abc",
            "message": "hi",
            "context": {},
        }
    )
    return client.post("/api/chat/execute/stream", json=body)


# --- stream route -------------------------------------------------------------


def test_stream_route_sets_sse_headers_and_emits_token_then_complete(client):
    with _patched_stream(_FakeStreamingModel()):
        resp = _post_stream(client)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "no-transform" in resp.headers["cache-control"]
    assert resp.headers["x-accel-buffering"] == "no"

    frames = _frames(resp.text)
    assert [f["type"] for f in frames] == ["user_message", "token", "token", "complete"]
    assert frames[-1]["content"] == "Hello"


def test_stream_unknown_session_is_404(client):
    from open_notebook.exceptions import NotFoundError

    with patch(
        "api.routers.chat.get_session_or_404",
        new_callable=AsyncMock,
        side_effect=NotFoundError("x"),
    ):
        resp = _post_stream(client)
    assert resp.status_code == 404


def test_stream_invalid_body_is_422(client):
    resp = client.post("/api/chat/execute/stream", json={})
    assert resp.status_code == 422


def test_stream_route_rejects_get(client):
    assert client.get("/api/chat/execute/stream").status_code == 405


# --- buffered route -----------------------------------------------------------


def test_buffered_unknown_session_is_404(client):
    from open_notebook.exceptions import NotFoundError

    with patch(
        "api.routers.chat.get_session_or_404",
        new_callable=AsyncMock,
        side_effect=NotFoundError("x"),
    ):
        resp = client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:nope", "message": "hi", "context": {}},
        )
    assert resp.status_code == 404


def test_buffered_route_provisions_without_streaming(client):
    """Regression guard: the buffered turn must not ask for a streaming model."""
    from open_notebook.graphs.chat import call_model_with_messages

    class _State(TypedDict, total=False):
        messages: Annotated[list, add_messages]
        notebook: object
        model_override: str
        context: dict

    builder = StateGraph(_State)
    builder.add_node("agent", call_model_with_messages)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    graph = builder.compile(
        checkpointer=SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    )

    provision = AsyncMock(
        return_value=MagicMock(invoke=MagicMock(return_value=AIMessage("ok")))
    )
    with (
        patch("api.routers.chat.chat_graph", graph),
        patch(
            "api.routers.chat.get_session_or_404",
            new_callable=AsyncMock,
            return_value=("chat_session:abc", _session()),
        ),
        patch("api.routers.chat.repo_query", new_callable=AsyncMock, return_value=[]),
        patch("open_notebook.graphs.chat.provision_langchain_model", provision),
    ):
        resp = client.post(
            "/api/chat/execute",
            json={"session_id": "chat_session:abc", "message": "hi", "context": {}},
        )

    assert resp.status_code == 200, resp.text
    assert provision.await_args is not None
    assert "streaming" not in provision.await_args.kwargs
    state = graph.get_state({"configurable": {"thread_id": "chat_session:abc"}})
    assert [(m.type, m.content) for m in state.values["messages"]] == [
        ("human", "hi"),
        ("ai", "ok"),
    ]


def test_buffered_node_accepts_human_message():
    """Sanity: the real node consumes the payload shape the router builds."""
    from open_notebook.graphs.chat import call_model_with_messages

    state = {"messages": [HumanMessage(content="hi")], "notebook": None}
    model = MagicMock(invoke=MagicMock(return_value=AIMessage("ok")))
    with patch(
        "open_notebook.graphs.chat.provision_langchain_model",
        AsyncMock(return_value=model),
    ):
        result = call_model_with_messages(state, {"configurable": {}})  # type: ignore[arg-type]
    assert result["messages"].content == "ok"
