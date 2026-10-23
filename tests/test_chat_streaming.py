"""SSE event-sequence tests for the streaming chat endpoints (#1412).

Pins the wire contract both stream consumers depend on:

    user_message -> token… -> (context_indicators) -> complete
    error                                        (on failure)

plus the three behaviors the issue calls out explicitly: keepalive frames while
the model is in prefill, server-side cancellation (a client disconnect stops
generation instead of letting the model run to completion), and persistence of a
partial answer so a stopped turn survives.

Model, prompt and checkpointer are mocked; DB access is out of scope here
(`test_chat_routers_characterization.py` covers the request/response plumbing).
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.exceptions import ConfigurationError


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


def _empty_state(**overrides):
    """`get_state` side effect: a *fresh* state per read.

    The router mutates the snapshot it appended the question to, so returning
    one shared object would make the follow-up dedupe read see the question as
    already persisted.
    """

    def _state(*_args, **_kwargs):
        return _graph_state({"messages": [], **overrides})

    return _state


def _http_request(*, disconnected=False):
    return SimpleNamespace(is_disconnected=AsyncMock(return_value=disconnected))


class _Msg:
    def __init__(self, id, type, content):
        self.id = id
        self.type = type
        self.content = content


class _Chunk:
    """A streamed model chunk with LangChain's `.content` shape."""

    def __init__(self, content):
        self.content = content


class _FakeStreamingModel:
    def __init__(self, chunks, on_stream=None):
        self._chunks = chunks
        self._on_stream = on_stream
        self.streamed = False

    async def astream(self, _payload):
        self.streamed = True
        for chunk in self._chunks:
            if self._on_stream is not None:
                await self._on_stream()
            yield chunk


async def _collect(gen):
    """Drain an SSE generator into a list of (kind, payload) tuples.

    `kind` is ``"comment"`` for `: ping` keepalive frames and ``"event"``
    otherwise (payload parsed from the JSON data line).
    """
    out = []
    async for frame in gen:
        if frame.startswith(":"):
            out.append(("comment", frame.strip()))
            continue
        assert frame.startswith("data: ")
        out.append(("event", json.loads(frame[len("data: ") :])))
    return out


def _types(frames):
    return [p["type"] for k, p in frames if k == "event"]


def _text(frames):
    return "".join(
        p["content"] for k, p in frames if k == "event" and p["type"] == "token"
    )


async def _stream_chat(model, *, message="hi", http_request=None, session=None):
    """Run the notebook stream generator with everything else mocked out."""
    from api.routers.chat import ExecuteChatRequest, _stream_execute_chat

    request = ExecuteChatRequest(
        session_id="chat_session:abc",
        message=message,
        context={},
        model_override=None,
    )

    update = MagicMock()

    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch(
            "api.routers.chat.provision_langchain_model",
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        frames = await _collect(
            _stream_execute_chat(
                request,
                http_request or _http_request(),  # type: ignore[arg-type]
                "chat_session:abc",
                session or _session(),
                None,
                None,
            )
        )
    return frames, update


# --- notebook chat: /chat/execute/stream --------------------------------------


@pytest.mark.asyncio
async def test_notebook_stream_event_sequence_and_persistence():
    """Tokens stream in order, then `complete`; the turn is checkpointed once."""
    model = _FakeStreamingModel([_Chunk("Hel"), _Chunk("lo "), _Chunk("world")])

    frames, update = await _stream_chat(model)

    assert _types(frames) == ["user_message", "token", "token", "token", "complete"]
    assert _text(frames) == "Hello world"
    assert frames[-1][1]["content"] == "Hello world"

    # Question first, then the answer: exactly two checkpoint writes.
    assert update.call_count == 2
    question = update.call_args_list[0].args[1]["messages"][0]
    assert question.content == "hi"
    written = update.call_args_list[1].args[1]["messages"][0]
    assert written.content == "Hello world"
    assert written.type == "ai"


@pytest.mark.asyncio
async def test_notebook_stream_strips_thinking_from_answer():
    """`complete` carries cleaned text and the checkpoint matches it."""
    model = _FakeStreamingModel([_Chunk(" thinkinghmm</think>"), _Chunk("answer")])

    frames, update = await _stream_chat(model)

    complete = [p for k, p in frames if k == "event" and p["type"] == "complete"][0]
    assert complete["content"] == "answer"
    written = update.call_args_list[1].args[1]["messages"][0]
    assert written.content == "answer"


@pytest.mark.asyncio
async def test_notebook_stream_emits_keepalive_while_generating():
    """A keepalive comment goes out when the model is silent past the interval."""
    from api.routers._sse import StreamOutcome, stream_events

    async def slow():
        await asyncio.sleep(0.2)

    model = _FakeStreamingModel([_Chunk("alpha "), _Chunk("beta")], on_stream=slow)

    with patch("api.routers._sse.KEEPALIVE_INTERVAL_SECONDS", 0.05):
        frames, _ = await _stream_chat(model)

    assert [p for k, p in frames if k == "comment"], "expected a keepalive comment"
    assert _types(frames)[-1] == "complete"
    assert _text(frames) == "alpha beta"

    # And the pump itself keeps pinging on a silent queue.
    queue: asyncio.Queue = asyncio.Queue()
    outcome = StreamOutcome()
    comment = await stream_events(queue, outcome, interval=0.01).__anext__()
    assert comment == ": ping\n\n"


@pytest.mark.asyncio
async def test_notebook_stream_persists_partial_when_response_task_is_cancelled():
    """Starlette cancels the response task on disconnect — teardown must survive.

    Inside an already-cancelled task a bare `await` raises immediately, so the
    settle step has to run in a shielded task of its own.
    """
    from api.routers.chat import ExecuteChatRequest, _stream_execute_chat

    class _BlockingModel:
        async def astream(self, _payload):
            yield _Chunk("partial")
            await asyncio.sleep(30)

    request = ExecuteChatRequest(
        session_id="chat_session:abc",
        message="hi",
        context={},
        model_override=None,
    )
    update = MagicMock()

    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch(
            "api.routers.chat.provision_langchain_model",
            new_callable=AsyncMock,
            return_value=_BlockingModel(),
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        gen = _stream_execute_chat(
            request,
            _http_request(),
            "chat_session:abc",
            _session(),
            None,
            None,  # type: ignore[arg-type]
        )

        async def consume():
            async for _ in gen:
                pass

        consumer = asyncio.create_task(consume())
        await asyncio.sleep(0.1)  # let the first token through
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

        for _ in range(50):
            if update.call_count >= 2:
                break
            await asyncio.sleep(0.02)

    assert update.call_count == 2
    written = update.call_args_list[1].args[1]["messages"][0]
    assert written.content == "partial"


@pytest.mark.asyncio
async def test_notebook_stream_error_event_and_question_rolled_back():
    """A model failure emits a single `error` event and drops the question."""

    update = MagicMock()

    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch(
            "api.routers.chat.provision_langchain_model",
            new_callable=AsyncMock,
            side_effect=ConfigurationError("no model configured"),
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
        patch("api.routers.chat.discard_message", new_callable=AsyncMock) as discard,
    ):
        from api.routers.chat import ExecuteChatRequest, _stream_execute_chat

        request = ExecuteChatRequest(
            session_id="chat_session:abc",
            message="hi",
            context={},
            model_override=None,
        )
        frames = await _collect(
            _stream_execute_chat(
                request,
                _http_request(),
                "chat_session:abc",
                _session(),
                None,
                None,  # type: ignore[arg-type]
            )
        )

    errors = [p for k, p in frames if k == "event" and p["type"] == "error"]
    assert len(errors) == 1
    assert errors[0]["message"] == "no model configured"
    assert "complete" not in _types(frames)

    # The pending question was written, then rolled back — no answer persisted.
    assert update.call_count == 1
    discard.assert_awaited_once()
    question = update.call_args_list[0].args[1]["messages"][0]
    assert question.content == "hi"


@pytest.mark.asyncio
async def test_notebook_stream_empty_reply_is_an_error():
    frames, _ = await _stream_chat(_FakeStreamingModel([_Chunk("   ")]))

    assert _types(frames)[-1] == "error"
    assert (
        "empty"
        in [p["message"] for k, p in frames if k == "event" and p["type"] == "error"][0]
    )


@pytest.mark.asyncio
async def test_notebook_stream_persists_partial_on_disconnect():
    """Tearing the generator down mid-stream saves the partial answer."""
    from api.routers.chat import ExecuteChatRequest, _stream_execute_chat

    class _SlowModel:
        async def astream(self, _payload):
            yield _Chunk("partial")
            await asyncio.sleep(0.3)
            yield _Chunk("never")

    request = ExecuteChatRequest(
        session_id="chat_session:abc",
        message="hi",
        context={},
        model_override=None,
    )
    update = MagicMock()

    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch(
            "api.routers.chat.provision_langchain_model",
            new_callable=AsyncMock,
            return_value=_SlowModel(),
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        gen = _stream_execute_chat(
            request,
            _http_request(),
            "chat_session:abc",
            _session(),
            None,
            None,  # type: ignore[arg-type]
        )
        collected = []
        async for frame in gen:
            collected.append(frame)
            if len(collected) == 2:  # after user_message + first token
                break
        await gen.aclose()

    warnings = [f for f in collected if "keepalive" in f]
    assert not warnings  # sanity: nothing but the first token yet

    # The generator's `finally` persisted what had arrived before the close.
    assert update.call_count == 2
    written = update.call_args_list[1].args[1]["messages"][0]
    assert written.content == "partial"


@pytest.mark.asyncio
async def test_notebook_stream_stops_on_client_disconnect():
    """A reported disconnect ends the stream and cancels the model request."""
    cancelled = asyncio.Event()

    class _HangingModel:
        async def astream(self, _payload):
            yield _Chunk("x")
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    frames, _ = await _stream_chat(
        _HangingModel(), http_request=_http_request(disconnected=True)
    )
    await asyncio.wait_for(cancelled.wait(), timeout=2)

    assert cancelled.is_set()
    assert "complete" not in _types(frames)


# --- source chat: per-token events --------------------------------------------


async def _stream_source(model, *, http_request=None, session=None):
    """Run the source stream generator with context building and graph mocked."""
    from api.routers import source_chat as sc

    updates = {
        "context_indicators": {"sources": ["source:xyz"], "insights": [], "notes": []}
    }
    turn = SimpleNamespace(payload=["payload"], updates=updates)

    update = MagicMock()

    with (
        patch.object(sc, "source_chat_graph") as graph,
        patch.object(sc, "prepare_source_chat_turn", return_value=turn),
        patch.object(
            sc, "provision_langchain_model", new_callable=AsyncMock, return_value=model
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        frames = await _collect(
            sc.stream_source_chat_response(
                "chat_session:abc",
                "source:xyz",
                "hi",
                http_request=http_request or _http_request(),
                session=session or _session(),
            )
        )
    return frames, update


@pytest.mark.asyncio
async def test_source_chat_stream_emits_tokens_then_complete():
    frames, update = await _stream_source(
        _FakeStreamingModel([_Chunk("Hey"), _Chunk(" there")])
    )

    assert _types(frames) == [
        "user_message",
        "token",
        "token",
        "context_indicators",
        "complete",
    ]
    assert _text(frames) == "Hey there"
    assert [
        p["data"]
        for k, p in frames
        if k == "event" and p["type"] == "context_indicators"
    ] == [{"sources": ["source:xyz"], "insights": [], "notes": []}]

    # The answer write carries the node's state delta (indicators included).
    answer_write = update.call_args_list[1].args[1]
    assert answer_write["messages"][0].content == "Hey there"
    assert answer_write["context_indicators"]["sources"] == ["source:xyz"]
    assert update.call_args_list[0].kwargs["as_node"] == "source_chat_agent"


@pytest.mark.asyncio
async def test_source_chat_stream_persists_partial_on_disconnect():
    from api.routers import source_chat as sc

    class _SlowModel:
        async def astream(self, _payload):
            yield _Chunk("half")
            await asyncio.sleep(0.3)
            yield _Chunk("never")

    update = MagicMock()

    with (
        patch.object(sc, "source_chat_graph") as graph,
        patch.object(
            sc,
            "prepare_source_chat_turn",
            return_value=SimpleNamespace(payload=["p"], updates={}),
        ),
        patch.object(
            sc,
            "provision_langchain_model",
            new_callable=AsyncMock,
            return_value=_SlowModel(),
        ),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        gen = sc.stream_source_chat_response(
            "chat_session:abc", "source:xyz", "hi", session=_session()
        )
        collected = []
        async for frame in gen:
            collected.append(frame)
            if len(collected) == 2:
                break
        await gen.aclose()

    written = update.call_args_list[1].args[1]["messages"][0]
    assert written.content == "half"


# --- model provisioning --------------------------------------------------------


@pytest.mark.asyncio
async def test_notebook_stream_provisions_a_streaming_model():
    """`astream` needs an explicit `streaming=True`; Esperanto defaults it off."""
    from api.routers.chat import ExecuteChatRequest, _stream_execute_chat

    provision = AsyncMock(return_value=_FakeStreamingModel([_Chunk("x")]))
    request = ExecuteChatRequest(
        session_id="chat_session:abc",
        message="hi",
        context={},
        model_override=None,
    )
    update = MagicMock()

    with (
        patch("api.routers.chat.chat_graph") as graph,
        patch("api.routers.chat.build_chat_payload", return_value=["payload"]),
        patch("api.routers.chat.provision_langchain_model", provision),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=update),
    ):
        await _collect(
            _stream_execute_chat(
                request, _http_request(), "chat_session:abc", _session(), None, None
            )
        )

    assert provision.await_args is not None
    assert provision.await_args.kwargs["streaming"] is True


@pytest.mark.asyncio
async def test_source_stream_provisions_a_streaming_model():
    from api.routers import source_chat as sc

    provision = AsyncMock(return_value=_FakeStreamingModel([_Chunk("x")]))

    with (
        patch.object(sc, "source_chat_graph") as graph,
        patch.object(
            sc,
            "prepare_source_chat_turn",
            return_value=SimpleNamespace(payload=["p"], updates={}),
        ),
        patch.object(sc, "provision_langchain_model", provision),
        patch.object(graph, "get_state", side_effect=_empty_state()),
        patch.object(graph, "update_state", new=MagicMock()),
    ):
        await _collect(
            sc.stream_source_chat_response(
                "chat_session:abc", "source:xyz", "hi", session=_session()
            )
        )

    assert provision.await_args is not None
    assert provision.await_args.kwargs["streaming"] is True


# --- route wiring -------------------------------------------------------------


def test_stream_route_registered_and_sets_no_buffer_headers():
    import api.main as main

    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/api/chat/execute/stream" in paths

    from api.routers._sse import stream_headers

    headers = stream_headers()
    assert headers["Cache-Control"] == "no-cache, no-transform"
    assert headers["X-Accel-Buffering"] == "no"


def test_buffered_execute_endpoint_still_registered():
    """The non-streaming endpoint stays available for API consumers."""
    import api.main as main

    paths = {getattr(r, "path", None) for r in main.app.routes}
    assert "/api/chat/execute" in paths
