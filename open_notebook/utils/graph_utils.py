import asyncio
from typing import Any, Optional

from langchain_core.messages import AIMessage, BaseMessage, RemoveMessage
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


def invoke_chat_turn(
    graph, state: dict, config: RunnableConfig, user_message: BaseMessage
) -> Any:
    """Run one chat turn; if it fails, drop the unanswered question.

    Synchronous on purpose: call it via asyncio.to_thread so the invoke and the
    rollback run together in the worker thread, even if the request task is
    cancelled while waiting (client disconnect). Only the source-chat graph
    still runs this way; the notebook-chat graph is async and uses
    `ainvoke_chat_turn`.
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


async def ainvoke_chat_turn(
    graph, state: dict, config: RunnableConfig, user_message: BaseMessage
) -> Any:
    """Async twin of `invoke_chat_turn` for the async notebook-chat graph.

    The rollback is shielded so a cancellation that lands after the model call
    still removes the question; the shielded task finishes on its own.
    """
    try:
        return await graph.ainvoke(input=state, config=config)
    except BaseException:
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            await asyncio.shield(discard_message(graph, thread_id, user_message))
        raise


# --- Async helpers for the streaming endpoint ---------------------------------


async def persist_state(graph, thread_id: str, values: dict, *, as_node: str) -> None:
    """Write a checkpoint update off the event loop.

    `as_node` names the node the update is attributed to, so LangGraph advances
    the graph as if that node had produced it and stops replaying the node.
    """
    config = RunnableConfig(configurable={"thread_id": thread_id})
    await asyncio.to_thread(lambda: graph.update_state(config, values, as_node=as_node))


async def persist_pending_human_turn(
    graph, thread_id: str, message: BaseMessage, *, as_node: str
) -> bool:
    """Append the user's question to the checkpoint before generation starts.

    Tokens reach the client long before the graph would checkpoint its input, so
    the question is written up front: it must survive a stop during prefill (the
    client refetches the checkpoint afterwards) and be visible to a concurrent
    read. Keyed on the message id, so replaying the same message is a no-op.
    """
    config = RunnableConfig(configurable={"thread_id": thread_id})
    state = await asyncio.to_thread(graph.get_state, config=config)
    existing = (state.values or {}).get("messages", []) if state else []
    if message.id and any(getattr(m, "id", None) == message.id for m in existing):
        return False
    await persist_state(graph, thread_id, {"messages": [message]}, as_node=as_node)
    return True


async def discard_message(graph, thread_id: str, message: BaseMessage) -> None:
    """Async wrapper for `discard_unanswered_message`."""
    await asyncio.to_thread(discard_unanswered_message, graph, thread_id, message)


async def settle_streamed_turn(
    graph,
    thread_id: str,
    content: str,
    question: Optional[BaseMessage],
    *,
    as_node: str,
    keep_question: bool = False,
) -> None:
    """Persist what a streamed turn produced, or roll the question back.

    A partial answer is checkpointed as if the node had returned it, so it is
    kept in history and the graph is left complete. A turn that produced no text
    drops the question — unless `keep_question` is set (a stop or timeout, where
    the user asked and expects to see the question) — so a retry doesn't stack
    it twice. Raises on persistence failure: the caller decides how to report
    that.
    """
    if content.strip():
        await persist_state(
            graph,
            thread_id,
            {"messages": [AIMessage(content=content)]},
            as_node=as_node,
        )
        return
    if question is not None and not keep_question:
        await discard_message(graph, thread_id, question)


async def last_ai_content(graph, thread_id: str) -> str:
    """Return the thread's trailing AI message content, or "" if there is none.

    Used after a successful stream: the node checkpoints the *cleaned* answer,
    so this is more accurate than the accumulated token text.
    """
    config = RunnableConfig(configurable={"thread_id": thread_id})
    state = await asyncio.to_thread(graph.get_state, config=config)
    messages = (state.values or {}).get("messages", []) if state else []
    if not messages:
        return ""
    last = messages[-1]
    if getattr(last, "type", None) != "ai":
        return ""
    return str(last.content or "")
