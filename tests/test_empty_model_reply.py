"""An empty model reply is an error, not an answer (#1392).

Covers the graph nodes (notebook chat, source chat, Ask final answer) and the
router side of a failed turn: the user's question is removed from the thread
checkpoint so a retry doesn't duplicate it.
"""

import json
import sqlite3
from typing import Annotated, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_notebook.exceptions import IncompleteGenerationError

EMPTY_REPLIES = ["", "   \n\t", "<think>only reasoning</think>", None]


def _sync_model_returning(content: str) -> MagicMock:
    model = MagicMock()
    # AIMessage won't accept content=None; some providers still return it.
    reply = MagicMock(content=None) if content is None else AIMessage(content=content)
    model.invoke = MagicMock(return_value=reply)
    return model


# --- graph nodes -------------------------------------------------------------


@pytest.mark.parametrize("reply", EMPTY_REPLIES)
def test_notebook_chat_node_rejects_empty_reply(reply):
    from open_notebook.graphs.chat import call_model_with_messages

    state = {"messages": [HumanMessage(content="hi")], "notebook": None}
    with patch(
        "open_notebook.graphs.chat.provision_langchain_model",
        new=AsyncMock(return_value=_sync_model_returning(reply)),
    ):
        with pytest.raises(IncompleteGenerationError, match="empty response"):
            call_model_with_messages(state, {"configurable": {}})  # type: ignore[arg-type]


def test_notebook_chat_node_keeps_nonempty_reply():
    from open_notebook.graphs.chat import call_model_with_messages

    state = {"messages": [HumanMessage(content="hi")], "notebook": None}
    with patch(
        "open_notebook.graphs.chat.provision_langchain_model",
        new=AsyncMock(return_value=_sync_model_returning("<think>x</think>hello")),
    ):
        result = call_model_with_messages(state, {"configurable": {}})  # type: ignore[arg-type]
    assert result["messages"].content == "hello"


@pytest.mark.parametrize("reply", EMPTY_REPLIES)
def test_source_chat_node_rejects_empty_reply(reply):
    from open_notebook.graphs.source_chat import call_model_with_source_context

    state = {"source_id": "source:1", "messages": [HumanMessage(content="hi")]}
    with (
        patch(
            "open_notebook.graphs.source_chat.build_source_context",
            new=AsyncMock(return_value={"sources": [], "insights": []}),
        ),
        patch(
            "open_notebook.graphs.source_chat.provision_langchain_model",
            new=AsyncMock(return_value=_sync_model_returning(reply)),
        ),
    ):
        with pytest.raises(IncompleteGenerationError, match="empty response"):
            call_model_with_source_context(state, {"configurable": {}})  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", EMPTY_REPLIES)
async def test_ask_final_answer_rejects_empty_reply(reply):
    from open_notebook.graphs.ask import ThreadState, write_final_answer

    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=MagicMock(content=reply))
    with patch(
        "open_notebook.graphs.ask.provision_langchain_model",
        new=AsyncMock(return_value=model),
    ):
        with pytest.raises(IncompleteGenerationError, match="empty response"):
            await write_final_answer(
                cast(ThreadState, {"question": "q", "answers": ["a"]}),
                cast(RunnableConfig, {"configurable": {}}),
            )


# --- failed turn: no persisted blank answer, no duplicated question ----------


class _State(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    source_id: str
    model_override: str
    context_indicators: dict
    context: str
    notebook: object


def _toy_graph(replies: list):
    """A checkpointed graph whose node raises like the real one on an empty
    reply, then answers on the next call."""

    def node(state):
        reply = replies.pop(0)
        if not reply.strip():
            raise IncompleteGenerationError("The model returned an empty response.")
        return {"messages": AIMessage(content=reply)}

    builder = StateGraph(_State)
    builder.add_node("agent", node)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)
    saver = SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    return builder.compile(checkpointer=saver)


async def _events(gen):
    return [json.loads(chunk[len("data: ") :]) async for chunk in gen]


def _history(graph, thread_id):
    state = graph.get_state(RunnableConfig(configurable={"thread_id": thread_id}))
    return [(m.type, m.content) for m in state.values.get("messages", [])]


@pytest.mark.asyncio
async def test_source_chat_failed_turn_is_rolled_back_and_retry_is_clean():
    from api.routers.source_chat import stream_source_chat_response

    graph = _toy_graph(["", "the answer"])
    with patch("api.routers.source_chat.source_chat_graph", graph):
        failed = await _events(
            stream_source_chat_response("chat_session:s", "source:1", "question")
        )
        assert failed[-1] == {
            "type": "error",
            "message": "The model returned an empty response.",
        }
        assert not any(e["type"] == "ai_message" for e in failed)
        assert _history(graph, "chat_session:s") == []

        retried = await _events(
            stream_source_chat_response("chat_session:s", "source:1", "question")
        )

    assert [e["content"] for e in retried if e["type"] == "ai_message"] == [
        "the answer"
    ]
    assert _history(graph, "chat_session:s") == [
        ("human", "question"),
        ("ai", "the answer"),
    ]


def test_notebook_chat_failed_turn_is_rolled_back_and_retry_is_clean():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    graph = _toy_graph(["", "the answer"])
    session = MagicMock(model_override=None, save=AsyncMock())
    with (
        patch("api.routers.chat.chat_graph", graph),
        patch(
            "api.routers.chat.get_session_or_404",
            new=AsyncMock(return_value=("chat_session:n", session)),
        ),
        patch("api.routers.chat.repo_query", new=AsyncMock(return_value=[])),
    ):
        payload = {"session_id": "chat_session:n", "message": "question", "context": {}}
        failed = client.post("/api/chat/execute", json=payload)
        assert failed.status_code >= 400
        assert "empty response" in failed.json()["detail"]
        assert _history(graph, "chat_session:n") == []

        retried = client.post("/api/chat/execute", json=payload)

    assert retried.status_code == 200
    assert _history(graph, "chat_session:n") == [
        ("human", "question"),
        ("ai", "the answer"),
    ]


def test_discard_unanswered_message_keeps_earlier_turns():
    from open_notebook.utils.graph_utils import discard_unanswered_message

    graph = _toy_graph(["first answer", ""])
    config = RunnableConfig(configurable={"thread_id": "t"})
    graph.invoke({"messages": [HumanMessage(content="q1", id="h1")]}, config)

    pending = HumanMessage(content="q2", id="h2")
    with pytest.raises(IncompleteGenerationError):
        graph.invoke({"messages": [pending]}, config)
    assert _history(graph, "t")[-1] == ("human", "q2")

    discard_unanswered_message(graph, "t", pending)

    assert _history(graph, "t") == [("human", "q1"), ("ai", "first answer")]


def test_discard_unanswered_message_ignores_unknown_ids():
    from open_notebook.utils.graph_utils import discard_unanswered_message

    graph = _toy_graph(["first answer"])
    config = RunnableConfig(configurable={"thread_id": "t"})
    graph.invoke({"messages": [HumanMessage(content="q1", id="h1")]}, config)

    # Never reached the checkpoint (e.g. get_state failed before invoke).
    discard_unanswered_message(graph, "t", HumanMessage(content="x", id="nope"))

    assert _history(graph, "t") == [("human", "q1"), ("ai", "first answer")]
