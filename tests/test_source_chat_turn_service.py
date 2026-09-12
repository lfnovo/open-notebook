"""Unit tests for `api/source_chat_service.py` (source-chat turn coordination).

Covers the two policies the SSE router delegates to the service:

- the refcounted per-session lock (serialization, independence across sessions,
  eviction on normal release and on the cancelled-while-waiting path)
- the "persist the pending human turn unless it is already the trailing
  unanswered turn" decision, which keys on the client `message_id`
"""

import asyncio
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from api.source_chat_service import (
    _session_locks,
    persist_pending_human_turn,
    session_turn_lock,
    source_chat_turn,
)

CONFIG = RunnableConfig(configurable={"thread_id": "chat_session:abc"})


@pytest.fixture(autouse=True)
def clean_registry():
    _session_locks.clear()
    yield
    _session_locks.clear()


class FakeGraph:
    """A checkpoint graph with a fixed state snapshot, recording updates."""

    def __init__(self, values: Optional[dict] = None):
        self._values = values
        self.updates: list[Any] = []

    def get_state(self, config: RunnableConfig) -> Any:
        if self._values is None:
            return None
        return SimpleNamespace(values=self._values)

    async def aupdate_state(self, config: RunnableConfig, values: Any) -> None:
        self.updates.append(values)


# --- session lock -------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_serializes_two_turns_for_one_session():
    """The second turn cannot enter while the first holds the lock."""
    session_id = "chat_session:serialize"
    order: list[str] = []
    first_inside = asyncio.Event()
    release_first = asyncio.Event()

    async def first():
        async with session_turn_lock(session_id):
            order.append("first:enter")
            first_inside.set()
            await release_first.wait()
            order.append("first:exit")

    async def second():
        async with session_turn_lock(session_id):
            order.append("second:enter")
            order.append("second:exit")

    first_task = asyncio.create_task(first())
    await first_inside.wait()
    second_task = asyncio.create_task(second())
    await asyncio.sleep(0.01)

    assert order == ["first:enter"]

    release_first.set()
    await asyncio.gather(first_task, second_task)

    assert order == ["first:enter", "first:exit", "second:enter", "second:exit"]


@pytest.mark.asyncio
async def test_lock_is_independent_across_sessions():
    """A turn for one session never blocks a turn for another."""
    release = asyncio.Event()
    holding = asyncio.Event()
    other_entered = asyncio.Event()

    async def hold():
        async with session_turn_lock("chat_session:a"):
            holding.set()
            await release.wait()

    async def other():
        async with session_turn_lock("chat_session:b"):
            other_entered.set()

    hold_task = asyncio.create_task(hold())
    await holding.wait()

    await asyncio.wait_for(other(), timeout=1.0)
    assert other_entered.is_set()

    release.set()
    await hold_task


@pytest.mark.asyncio
async def test_lock_entry_evicted_when_last_holder_releases():
    """The registry entry survives while any holder is registered (including a
    waiter) and is dropped once the last one releases."""
    session_id = "chat_session:evict"
    waiter_done = asyncio.Event()

    async def waiter():
        async with session_turn_lock(session_id):
            waiter_done.set()

    async with session_turn_lock(session_id):
        assert _session_locks[session_id].holders == 1
        waiter_task = asyncio.create_task(waiter())
        await asyncio.sleep(0.01)
        assert _session_locks[session_id].holders == 2
        assert not waiter_done.is_set()

    await waiter_task
    assert waiter_done.is_set()
    assert session_id not in _session_locks


@pytest.mark.asyncio
async def test_lock_entry_evicted_when_waiter_is_cancelled():
    """A turn cancelled while waiting to acquire drops its holder without
    releasing an unheld lock, so the entry is still evicted."""
    session_id = "chat_session:cancel-acquire"
    holding = asyncio.Event()
    release = asyncio.Event()

    async def hold():
        async with session_turn_lock(session_id):
            holding.set()
            await release.wait()

    async def waiter():
        async with session_turn_lock(session_id):
            pytest.fail("waiter should have been cancelled before acquiring")

    hold_task = asyncio.create_task(hold())
    await holding.wait()

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.01)
    assert _session_locks[session_id].holders == 2

    waiter_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter_task
    assert _session_locks[session_id].holders == 1

    release.set()
    await hold_task
    assert session_id not in _session_locks


# --- pending human turn -------------------------------------------------------


@pytest.mark.asyncio
async def test_matching_message_id_skips_the_append():
    """A retry that reuses the id of the trailing unanswered turn is skipped."""
    graph = FakeGraph({"messages": [HumanMessage(content="hello", id="msg-1")]})

    appended = await persist_pending_human_turn(graph, CONFIG, "hello", "msg-1")

    assert appended is False
    assert graph.updates == []


@pytest.mark.asyncio
async def test_different_message_id_appends():
    """Two distinct identical messages carry distinct ids and are both kept."""
    graph = FakeGraph({"messages": [HumanMessage(content="hello", id="msg-1")]})

    appended = await persist_pending_human_turn(graph, CONFIG, "hello", "msg-2")

    assert appended is True
    (payload,) = graph.updates
    assert payload["messages"][0].content == "hello"
    assert payload["messages"][0].id == "msg-2"


@pytest.mark.asyncio
async def test_none_message_id_is_never_already_pending():
    graph = FakeGraph({"messages": [HumanMessage(content="hello", id=None)]})

    appended = await persist_pending_human_turn(graph, CONFIG, "hello", None)

    assert appended is True
    (payload,) = graph.updates
    assert payload["messages"][0].id is None


@pytest.mark.asyncio
async def test_trailing_ai_message_appends():
    """A completed exchange ends with an AI message, so the turn is not pending."""
    graph = FakeGraph(
        {
            "messages": [
                HumanMessage(content="hi", id="msg-1"),
                AIMessage(content="yo", id="msg-1"),
            ]
        }
    )

    appended = await persist_pending_human_turn(graph, CONFIG, "hello", "msg-1")

    assert appended is True
    (payload,) = graph.updates
    assert payload["messages"][0].content == "hello"


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [None, {}, {"messages": []}])
async def test_empty_checkpoint_appends(values):
    graph = FakeGraph(values)

    appended = await persist_pending_human_turn(graph, CONFIG, "hello", "msg-1")

    assert appended is True
    assert len(graph.updates) == 1


# --- composed turn ------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_chat_turn_persists_and_holds_the_lock():
    session_id = "chat_session:turn"
    graph = FakeGraph({"messages": []})

    async with source_chat_turn(
        graph=graph,
        session_id=session_id,
        config=CONFIG,
        message="hello",
        message_id="msg-1",
    ):
        assert _session_locks[session_id].lock.locked()
        assert len(graph.updates) == 1

    assert session_id not in _session_locks
