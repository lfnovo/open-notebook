"""Turn coordination for source chat.

Owns the policy a source-chat turn needs before generation can start: the
per-session lock that serializes the snapshot -> append -> invoke sequence, and
the decision to persist the pending human turn. The graph is passed in so the
caller's module attribute stays authoritative and this module is usable
standalone.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, Protocol

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig


class CheckpointGraph(Protocol):
    """The slice of a compiled LangGraph a turn needs."""

    def get_state(self, config: RunnableConfig) -> Any: ...

    async def aupdate_state(self, config: RunnableConfig, values: Any) -> Any: ...


# Per-session locks serialize the read-modify-write sequence (snapshot -> append
# user message -> invoke). Without them, two concurrent requests for the same
# thread could both read the same trailing message and each start a generation.
# Created lazily; refcounted so the entry is evicted once the last holder
# releases — a long-lived process must not keep one lock per session it has ever
# seen.
class _SessionLock:
    __slots__ = ("lock", "holders")

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.holders = 0


_session_locks: dict[str, _SessionLock] = {}


def _register_holder(session_id: str) -> _SessionLock:
    # No `await` between these dict ops, so on a single event loop the
    # read/create/increment is atomic. Registering the caller as a holder before
    # it awaits `acquire` keeps the entry alive until it releases.
    entry = _session_locks.get(session_id)
    if entry is None:
        entry = _SessionLock()
        _session_locks[session_id] = entry
    entry.holders += 1
    return entry


def _drop_holder(session_id: str, entry: _SessionLock) -> None:
    entry.holders -= 1
    # The `is entry` guard is defensive: the entry is only evicted when this was
    # the last holder, so `session_id` must still map to this same entry.
    if entry.holders == 0 and _session_locks.get(session_id) is entry:
        _session_locks.pop(session_id, None)


@asynccontextmanager
async def session_turn_lock(session_id: str) -> AsyncIterator[None]:
    """Hold the session's turn lock for the duration of the block."""
    entry = _register_holder(session_id)
    acquired = False
    try:
        await entry.lock.acquire()
        acquired = True
        yield
    finally:
        # Cancelled while waiting to acquire: drop the holder registered above
        # without releasing an unheld lock.
        if acquired:
            entry.lock.release()
        _drop_holder(session_id, entry)


async def persist_pending_human_turn(
    graph: CheckpointGraph,
    config: RunnableConfig,
    message: str,
    message_id: Optional[str] = None,
) -> bool:
    """Append the user message to the checkpoint unless it is already pending.

    Persisting up front makes the message survive a mid-generation disconnect
    (the frontend refetches the checkpoint on cancel/complete and would
    otherwise drop it). The guard keys on the client message id, not content: a
    retry that reuses the same id is deduplicated, while two distinct identical
    messages get distinct ids and are both kept. A completed exchange always
    ends with an AI message, so a trailing human turn is necessarily still
    pending.

    Returns whether the message was appended.
    """
    # SqliteSaver has no async read, so snapshot off the event loop.
    current_state = await asyncio.to_thread(graph.get_state, config=config)
    already_pending = False
    if current_state and current_state.values and "messages" in current_state.values:
        existing_messages = current_state.values["messages"]
        last_message = existing_messages[-1] if existing_messages else None
        already_pending = (
            isinstance(last_message, HumanMessage)
            and message_id is not None
            and getattr(last_message, "id", None) == message_id
        )
    if already_pending:
        return False
    await graph.aupdate_state(
        config, {"messages": [HumanMessage(content=message, id=message_id)]}
    )
    return True


@asynccontextmanager
async def source_chat_turn(
    graph: CheckpointGraph,
    session_id: str,
    config: RunnableConfig,
    message: str,
    message_id: Optional[str] = None,
) -> AsyncIterator[None]:
    """Serialize and persist one source-chat turn, then run the caller's block.

    The lock is held for the whole block so a concurrent request for the same
    thread cannot snapshot the same trailing message and start a second
    generation.
    """
    async with session_turn_lock(session_id):
        await persist_pending_human_turn(graph, config, message, message_id)
        yield
