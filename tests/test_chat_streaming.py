"""Streaming chat endpoint: token events, thinking filter, stop and timeout.

The endpoint runs the chat *graph* with `stream_mode="messages"`; these tests
drive it with a toy graph whose node streams through a fake chat model, so the
SSE envelope, the partial-answer settlement and the filters are exercised
without a provider.
"""

import asyncio
import json
import sqlite3
from typing import Annotated, AsyncIterator, Optional, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from api.routers._sse import (
    LEAD_BUFFER_LIMIT,
    StreamOutcome,
    ThinkingFilter,
    format_error_event,
    stream_events,
)
from api.routers.chat import ExecuteChatRequest, _stream_execute_chat
from open_notebook.exceptions import IncompleteGenerationError
from open_notebook.utils.checkpointing import HybridSqliteSaver
from open_notebook.utils.graph_utils import persist_state


class _State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    context: dict
    notebook: object
    model_override: Optional[str]


class StreamingFakeModel(BaseChatModel):
    """Chat model that emits `chunks` one at a time from `_astream`."""

    chunks: list[str]
    delay: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "streaming-fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content="".join(self.chunks)))
            ]
        )

    async def _astream(
        self,
        messages,
        stop=None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for piece in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=piece))
            if run_manager:
                await run_manager.on_llm_new_token(piece, chunk=chunk)
            yield chunk


def _graph_that_streams(chunks: list[str], delay: float = 0.0):
    """One-node graph whose node streams `chunks` and checkpoints the reply."""

    model = StreamingFakeModel(chunks=chunks, delay=delay, streaming=True)

    async def node(state, config):
        ai = await model.ainvoke([HumanMessage(content="x")])
        text = str(ai.content)
        cleaned = text.split("</think>", 1)[1] if "</think>" in text else text
        return {"messages": [AIMessage(content=cleaned)]}

    builder = StateGraph(_State)
    builder.add_node("agent", node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    saver = HybridSqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    return builder.compile(checkpointer=saver)


class FakeHttpRequest:
    """`Request` stand-in counting is_disconnected() polls."""

    def __init__(self, disconnect_after: Optional[int] = None):
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.disconnect_after is not None and self.calls > self.disconnect_after


def _http(disconnect_after: Optional[int] = None) -> Request:
    return cast(Request, FakeHttpRequest(disconnect_after))


def _request(message: str = "question") -> ExecuteChatRequest:
    return ExecuteChatRequest(session_id="chat_session:s", message=message, context={})


async def _drain(gen) -> list[dict]:
    events = []
    async for frame in gen:
        if frame.startswith("data: "):
            events.append(json.loads(frame[len("data: ") :]))
    return events


def _history(graph, thread_id: str):
    state = graph.get_state(RunnableConfig(configurable={"thread_id": thread_id}))
    return [(m.type, m.content) for m in state.values.get("messages", [])]


# --- ThinkingFilter ----------------------------------------------------------


def test_filter_strips_whole_thinking_block():
    f = ThinkingFilter()
    assert f.feed("thinking hard</think>") == ""
    assert f.feed("hello") == "hello"


def test_filter_handles_tags_split_across_chunks():
    f = ThinkingFilter()
    out = "".join(
        f.feed(piece) for piece in ["<thi", "nk>hide", "</thi", "nk>ans", "wer"]
    )
    assert out == "answer"


def test_filter_strips_stray_close_tag_after_a_long_preamble():
    f = ThinkingFilter()
    out = f.feed("p" * 500) + f.feed("</think") + f.feed(">answer")
    assert out == "p" * 500 + "answer"


def test_filter_keeps_a_partial_open_tag_at_the_lead_limit():
    f = ThinkingFilter()
    preamble = "p" * (LEAD_BUFFER_LIMIT + 1) + "<thi"
    out = f.feed(preamble) + f.feed("nk>hidden</think>visible")
    assert out == "p" * (LEAD_BUFFER_LIMIT + 1) + "visible"


def test_filter_strips_tagless_preamble():
    f = ThinkingFilter()
    out = f.feed("reasoning here</think") + f.feed(">answer") + f.flush()
    assert out == "answer"


def test_filter_strips_an_open_tag_that_appears_in_the_body():
    f = ThinkingFilter()
    out = f.feed("p" * 500 + " mid") + f.feed(" thinkinghidden</think>tail")
    assert out == "p" * 500 + " mid" + "tail"


def test_filter_drops_unterminated_thinking_block():
    f = ThinkingFilter()
    assert f.feed(" thinking still reasoning") == ""
    assert f.flush() == ""


def test_filter_passes_plain_text_through():
    f = ThinkingFilter()
    assert f.feed("plain ") + f.feed("text") + f.flush() == "plain text"


# --- error envelope ----------------------------------------------------------


def test_format_error_event_truncates_typed_message():
    frame = format_error_event(IncompleteGenerationError("x" * 500))
    message = json.loads(frame[len("data: ") :])["message"]
    assert len(message) == 200


# --- keepalive / deadline ----------------------------------------------------


@pytest.mark.asyncio
async def test_idle_stream_emits_keepalive_comments():
    queue: asyncio.Queue = asyncio.Queue()
    outcome = StreamOutcome()
    frames = [
        frame
        async for frame in stream_events(queue, outcome, interval=0.01, timeout=0.05)
    ]
    assert frames, "expected keepalive frames"
    assert all(frame == ": ping\n\n" for frame in frames)
    assert outcome.kind == "timeout"


@pytest.mark.asyncio
async def test_deadline_is_enforced_while_tokens_arrive():
    queue: asyncio.Queue = asyncio.Queue()
    outcome = StreamOutcome()

    async def producer():
        while True:
            await queue.put(("token", "x"))
            await asyncio.sleep(0.005)

    task = asyncio.create_task(producer())
    try:
        frames = [
            frame
            async for frame in stream_events(
                queue, outcome, interval=0.01, timeout=0.05
            )
        ]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert len(frames) > 3  # tokens never stopped arriving
    assert outcome.kind == "timeout"


# --- endpoint ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_emits_tokens_then_cleaned_complete(monkeypatch):
    import api.routers.chat as chat_router

    graph = _graph_that_streams(
        ["Hid", "den ", "thought", "</think>", "The ", "answer."]
    )
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    events = await _drain(
        _stream_execute_chat(_request(), _http(), "s", session, None, None)
    )

    types = [e["type"] for e in events]
    assert types[0] == "user_message"
    assert types[-1] == "complete"
    streamed = "".join(e["content"] for e in events if e["type"] == "token")
    assert streamed == "The answer."
    assert events[-1]["content"] == "The answer."
    assert _history(graph, "s") == [("human", "question"), ("ai", "The answer.")]


@pytest.mark.asyncio
async def test_stop_keeps_the_partial_answer(monkeypatch):
    import api.routers.chat as chat_router

    graph = _graph_that_streams(["Part ", "ial", " answer"], delay=0.01)
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    # Let one token through, then report the client gone.
    http = _http(1)
    events = await _drain(
        _stream_execute_chat(_request(), http, "s2", session, None, None)
    )

    assert not any(e["type"] == "complete" for e in events)
    history = _history(graph, "s2")
    assert history[0] == ("human", "question")
    assert history[-1][0] == "ai"
    assert history[-1][1].startswith("Part")


@pytest.mark.asyncio
async def test_stop_before_first_token_keeps_the_question(monkeypatch):
    import api.routers._sse as sse_module
    import api.routers.chat as chat_router

    monkeypatch.setattr(sse_module, "DISCONNECT_POLL_SECONDS", 0.02)
    graph = _graph_that_streams(["late"], delay=0.3)
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    http = _http(1)
    await _drain(_stream_execute_chat(_request(), http, "s3", session, None, None))

    # The question was accepted and shown to the client; stopping during
    # prefill keeps it as an unanswered turn rather than losing it.
    assert _history(graph, "s3") == [("human", "question")]


@pytest.mark.asyncio
async def test_failed_turn_drops_the_unanswered_question(monkeypatch):
    import api.routers.chat as chat_router

    async def node(state, config):
        raise RuntimeError("provider exploded")

    builder = StateGraph(_State)
    builder.add_node("agent", node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    graph = builder.compile(
        checkpointer=HybridSqliteSaver(
            sqlite3.connect(":memory:", check_same_thread=False)
        )
    )
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    events = await _drain(
        _stream_execute_chat(_request(), _http(), "s6", session, None, None)
    )

    assert events[-1]["type"] == "error"
    # A retry would otherwise stack the same question twice.
    assert _history(graph, "s6") == []


@pytest.mark.asyncio
async def test_timeout_stops_the_run_before_settling(monkeypatch):
    import api.routers._sse as sse_module
    import api.routers.chat as chat_router

    monkeypatch.setattr(sse_module, "MAX_STREAM_SECONDS", 0.2)
    # A slow stream: the run is still producing when the deadline passes. The
    # first chunk is longer than the thinking filter's lead buffer, so it is
    # released to the client at once.
    graph = _graph_that_streams(["part" * 120, " ial"], delay=0.15)
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    await _drain(_stream_execute_chat(_request(), _http(), "s7", session, None, None))
    after_settle = _history(graph, "s7")

    # Give a still-running task time to checkpoint over the settlement.
    await asyncio.sleep(0.2)

    assert _history(graph, "s7") == after_settle
    assert after_settle[0] == ("human", "question")
    assert after_settle[-1][0] == "ai"


@pytest.mark.asyncio
async def test_settlement_survives_refiring_cancellation(monkeypatch):
    """Cancellation that re-fires (anyio cancel scope, as Starlette uses) must
    not cut the partial answer off. The teardown has to be finished by the time
    the generator ends, not left running behind it."""
    import anyio

    import api.routers.chat as chat_router

    graph = _graph_that_streams(["part" * 120] + [" more"] * 20, delay=0.02)
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(save=AsyncMock())

    settled = asyncio.Event()
    original_settle = chat_router.settle_turn_end

    async def spy_settle(*args, **kwargs):
        result = await original_settle(*args, **kwargs)
        settled.set()
        return result

    monkeypatch.setattr(chat_router, "settle_turn_end", spy_settle)

    async def consume() -> None:
        async for _ in _stream_execute_chat(
            _request(), _http(), "s8", session, None, None
        ):
            pass

    with anyio.CancelScope() as scope:

        async def cancel_soon() -> None:
            await anyio.sleep(0.1)
            scope.cancel()

        async with anyio.create_task_group() as tg:
            tg.start_soon(cancel_soon)
            await consume()

    # The client is gone at this point; nobody drives the generator any more.
    # The detached teardown has to finish by itself and persist the partial.
    for _ in range(100):
        if settled.is_set():
            break
        await anyio.sleep(0.02)

    assert settled.is_set()
    history = _history(graph, "s8")
    assert history[0] == ("human", "question")
    assert history[-1][0] == "ai"


@pytest.mark.asyncio
async def test_serialized_turn_excludes_and_evicts():
    from api.routers._chat_shared import _session_locks, serialized_turn

    order: list[str] = []

    async def worker(name: str) -> None:
        async with serialized_turn("chat_session:lock"):
            order.append(f"{name}-in")
            await asyncio.sleep(0.01)
            order.append(f"{name}-out")

    await asyncio.gather(worker("a"), worker("b"))

    assert order in (
        ["a-in", "a-out", "b-in", "b-out"],
        ["b-in", "b-out", "a-in", "a-out"],
    )
    # Last holder leaves: the entry is evicted, not kept for the process life.
    assert "chat_session:lock" not in _session_locks


@pytest.mark.asyncio
async def test_settle_policy_keeps_a_stopped_question_and_drops_a_failed_one():
    """The keep-or-drop rule lives with the settlement, not the router."""
    from open_notebook.utils.graph_utils import StreamEnd, settle_turn_end

    async def node(state, config):
        return {"messages": [AIMessage(content="x")]}

    builder = StateGraph(_State)
    builder.add_node("agent", node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    graph = builder.compile(
        checkpointer=HybridSqliteSaver(
            sqlite3.connect(":memory:", check_same_thread=False)
        )
    )

    async def seed(thread_id: str, question: HumanMessage) -> None:
        await persist_state(graph, thread_id, {"messages": [question]}, as_node="agent")

    stopped = HumanMessage(content="stopped", id="h1")
    await seed("stop", stopped)
    assert await settle_turn_end(
        graph, "stop", "", stopped, as_node="agent", end=StreamEnd.STOP
    )
    assert _history(graph, "stop") == [("human", "stopped")]

    failed = HumanMessage(content="failed", id="h2")
    await seed("error", failed)
    assert await settle_turn_end(
        graph, "error", "", failed, as_node="agent", end=StreamEnd.ERROR
    )
    assert _history(graph, "error") == []


@pytest.mark.asyncio
async def test_timeout_says_partial_kept_only_when_there_is_text(monkeypatch):
    import api.routers._sse as sse_module
    import api.routers.chat as chat_router

    session = MagicMock(save=AsyncMock())

    monkeypatch.setattr(sse_module, "MAX_STREAM_SECONDS", 1.0)
    chatty = _graph_that_streams(["reason", "</think>"] + ["chunk"] * 400, delay=0.005)
    monkeypatch.setattr(chat_router, "chat_graph", chatty)
    events = await _drain(
        _stream_execute_chat(_request(), _http(), "s4", session, None, None)
    )
    assert events[-1]["type"] == "error"
    assert "Partial answer kept." in events[-1]["message"]

    monkeypatch.setattr(sse_module, "MAX_STREAM_SECONDS", 0.3)
    silent = _graph_that_streams(["never"], delay=1.0)
    monkeypatch.setattr(chat_router, "chat_graph", silent)
    events = await _drain(
        _stream_execute_chat(_request(), _http(), "s5", session, None, None)
    )
    assert events[-1]["type"] == "error"
    assert "Partial answer kept." not in events[-1]["message"]


# --- HTTP route --------------------------------------------------------------


def test_stream_route_returns_event_stream(monkeypatch):
    from fastapi.testclient import TestClient

    import api.routers.chat as chat_router
    from api.main import app

    graph = _graph_that_streams(["Hello", " there"])
    monkeypatch.setattr(chat_router, "chat_graph", graph)
    session = MagicMock(model_override=None, save=AsyncMock())

    with (
        monkeypatch.context() as m,
    ):
        m.setattr(
            chat_router,
            "get_session_or_404",
            AsyncMock(return_value=("chat_session:h", session)),
        )
        m.setattr(chat_router, "repo_query", AsyncMock(return_value=[]))
        client = TestClient(app)
        with client.stream(
            "POST",
            "/api/chat/execute/stream",
            json={"session_id": "chat_session:h", "message": "hi", "context": {}},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["x-accel-buffering"] == "no"
            body = "".join(response.iter_text())

    events = [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert events[0]["type"] == "user_message"
    assert events[-1] == {"type": "complete", "content": "Hello there"}


def test_stream_route_404s_for_an_unknown_session(monkeypatch):
    from fastapi.testclient import TestClient

    import api.routers.chat as chat_router
    from api.main import app
    from open_notebook.exceptions import NotFoundError

    monkeypatch.setattr(
        chat_router,
        "get_session_or_404",
        AsyncMock(side_effect=NotFoundError("Session not found")),
    )

    client = TestClient(app)
    response = client.post(
        "/api/chat/execute/stream",
        json={"session_id": "chat_session:nope", "message": "hi", "context": {}},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_turns_on_one_session_serialize(monkeypatch):
    """Two turns racing one session must not build from the same history.

    Without the session lock both snapshot the empty thread, generate blind to
    each other and interleave their answers; the second prompt here would miss
    the first answer.
    """
    from uuid import uuid4

    import httpx
    from fastapi import FastAPI

    import api.routers.chat as chat_router
    import open_notebook.graphs.chat as chat_graph_module

    seen: list[list[tuple[str, str]]] = []

    class Model:
        async def ainvoke(self, messages):
            seen.append([(m.type, m.content) for m in messages])
            await asyncio.sleep(0.05)
            return AIMessage(content=f"answer {len(seen)}")

    thread_id = f"chat_session:serialized-{uuid4()}"
    session = MagicMock(model_override=None, save=AsyncMock())
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api")

    monkeypatch.setattr(
        chat_graph_module, "provision_langchain_model", AsyncMock(return_value=Model())
    )
    monkeypatch.setattr(
        chat_router,
        "get_session_or_404",
        AsyncMock(return_value=(thread_id, session)),
    )
    monkeypatch.setattr(chat_router, "repo_query", AsyncMock(return_value=[]))
    # The node and its state definition are the real ones; only the checkpoint
    # store is in-memory so the test leaves no thread in the file.
    graph = chat_graph_module.agent_state.compile(
        checkpointer=HybridSqliteSaver(
            sqlite3.connect(":memory:", check_same_thread=False)
        )
    )
    monkeypatch.setattr(chat_router, "chat_graph", graph)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:

        async def post(message: str):
            return await client.post(
                "/api/chat/execute",
                json={"session_id": thread_id, "message": message, "context": {}},
            )

        first, second = await asyncio.gather(post("first"), post("second"))

    assert first.status_code == 200 and second.status_code == 200

    # `seen` is the full payload: system prompt plus history. The first turn
    # saw one human message, the queued one saw the earlier question and its
    # answer too.
    assert sorted(len(prompt) for prompt in seen) == [2, 4]
    queued = max(seen, key=len)
    assert [content for kind, content in queued if kind == "human"] == [
        "first",
        "second",
    ]
    assert ("ai", "answer 1") in queued

    assert _history(graph, thread_id) == [
        ("human", "first"),
        ("ai", "answer 1"),
        ("human", "second"),
        ("ai", "answer 2"),
    ]


def test_buffered_route_runs_the_real_async_graph(monkeypatch):
    """`/api/chat/execute` must survive the node being async.

    The other route tests use toy graphs with sync nodes; the real node is
    `async def`, and `graph.invoke` refuses those ("no synchronous function").
    This runs the real compiled graph through the buffered route.
    """
    from uuid import uuid4

    from fastapi.testclient import TestClient

    import api.routers.chat as chat_router
    import open_notebook.graphs.chat as chat_graph_module
    from api.main import app

    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=AIMessage(content="a plain answer"))
    session = MagicMock(model_override=None, save=AsyncMock())
    thread_id = f"chat_session:buffered-{uuid4()}"
    # Real node and state, in-memory checkpoint store (no file thread left).
    graph = chat_graph_module.agent_state.compile(
        checkpointer=HybridSqliteSaver(
            sqlite3.connect(":memory:", check_same_thread=False)
        )
    )

    with (
        monkeypatch.context() as m,
    ):
        m.setattr(
            chat_graph_module,
            "provision_langchain_model",
            AsyncMock(return_value=model),
        )
        m.setattr(chat_router, "chat_graph", graph)
        m.setattr(
            chat_router,
            "get_session_or_404",
            AsyncMock(return_value=(thread_id, session)),
        )
        m.setattr(chat_router, "repo_query", AsyncMock(return_value=[]))
        client = TestClient(app)
        response = client.post(
            "/api/chat/execute",
            json={
                "session_id": thread_id,
                "message": "question",
                "context": {},
            },
        )

    assert response.status_code == 200
    assert [m["content"] for m in response.json()["messages"]] == [
        "question",
        "a plain answer",
    ]
    assert _history(graph, thread_id) == [
        ("human", "question"),
        ("ai", "a plain answer"),
    ]
