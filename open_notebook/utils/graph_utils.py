import asyncio
from typing import Any

from langchain_core.messages import BaseMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger


async def get_session_message_count(graph, session_id: str) -> int:
    """Get message count from LangGraph state, returns 0 on error."""
    try:
        # Use sync get_state() in a thread (SqliteSaver doesn't support async)
        thread_state = await asyncio.to_thread(
            graph.get_state,
            config=RunnableConfig(configurable={"thread_id": session_id}),
        )
        if thread_state and thread_state.values and "messages" in thread_state.values:
            return len(thread_state.values["messages"])
    except Exception as e:
        logger.warning(f"Could not fetch message count for session {session_id}: {e}")
    return 0


def discard_unanswered_message(graph, thread_id: str, message: BaseMessage) -> None:
    """Remove a user message whose turn failed from the thread's checkpoint.

    LangGraph checkpoints the graph input before running the nodes, so when the
    model call fails the question stays in history with no answer, and a retry
    adds it a second time. Synchronous (SqliteSaver). Best-effort: never raises,
    so it can't mask the original error.
    """
    if not message.id:
        return
    try:
        config = RunnableConfig(configurable={"thread_id": thread_id})
        state = graph.get_state(config)
        messages = (state.values or {}).get("messages", []) if state else []
        if any(getattr(m, "id", None) == message.id for m in messages):
            graph.update_state(config, {"messages": [RemoveMessage(id=message.id)]})
    except Exception:
        logger.exception(f"Could not discard unanswered message in {thread_id}")


async def persist_state(
    graph,
    thread_id: str,
    values: dict,
    *,
    as_node: str,
) -> None:
    """Write a checkpoint update off the event loop.

    Used by the streaming chat endpoints, which generate outside the graph:
    SqliteSaver has no async API (`aupdate_state` raises NotImplementedError),
    so the write goes through a worker thread exactly like `get_state` does.
    `as_node` names the node the update is attributed to — LangGraph cannot
    infer it for a single-node graph once a pending turn is scheduled.
    """
    config = RunnableConfig(configurable={"thread_id": thread_id})
    await asyncio.to_thread(lambda: graph.update_state(config, values, as_node=as_node))


async def persist_pending_human_turn(
    graph,
    thread_id: str,
    message: BaseMessage,
    *,
    as_node: str,
) -> bool:
    """Append the user's question to the checkpoint before generation starts.

    The streaming endpoints return tokens before the graph would ever
    checkpoint its input, so the question has to be written up front: it must
    survive a mid-generation disconnect (the frontend refetches the checkpoint
    on stop/complete) and be visible to a concurrent read. The guard keys on the
    message id, so a retry that reuses the id is deduplicated.

    Returns whether the message was written.
    """
    config = RunnableConfig(configurable={"thread_id": thread_id})
    state = await asyncio.to_thread(graph.get_state, config=config)
    existing = (state.values or {}).get("messages", []) if state else []
    if message.id and any(getattr(m, "id", None) == message.id for m in existing):
        return False
    await persist_state(graph, thread_id, {"messages": [message]}, as_node=as_node)
    return True


async def discard_message(graph, thread_id: str, message: BaseMessage) -> None:
    """Async wrapper for `discard_unanswered_message` (streaming endpoints)."""
    await asyncio.to_thread(discard_unanswered_message, graph, thread_id, message)


def invoke_chat_turn(
    graph, state: dict, config: RunnableConfig, user_message: BaseMessage
) -> Any:
    """Run one chat turn; if it fails, drop the unanswered question.

    Synchronous on purpose: call it via asyncio.to_thread so the invoke and the
    rollback run together in the worker thread, even if the request task is
    cancelled while waiting (client disconnect).
    """
    try:
        # LangGraph accepts a partial state dict at runtime, but its typed
        # signature requires the full state type.
        return graph.invoke(input=state, config=config)
    except Exception:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            discard_unanswered_message(graph, thread_id, user_message)
        raise
