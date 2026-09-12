"""Characterization coverage for the three interactive research runtimes.

These tests deliberately exercise runtime boundaries with database access and
language models mocked. They document behavior; they are not a redesign suite.
The one strict xfail records the future Source Chat contract from issue #1224.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from api.routers.chat import ExecuteChatRequest, execute_chat
from api.routers.search import stream_ask_response
from api.routers.source_chat import stream_source_chat_response
from open_notebook.graphs.ask import graph as ask_graph
from open_notebook.graphs.chat import call_model_with_messages
from open_notebook.graphs.chat import graph as notebook_chat_graph
from open_notebook.graphs.source_chat import (
    _call_model_with_source_context_inner,
    _format_source_context,
    source_chat_graph,
)
from open_notebook.utils.context_builder import build_source_context


def _topology(graph):
    drawable = graph.get_graph()
    nodes = set(drawable.nodes)
    edges = {(edge.source, edge.target, edge.conditional) for edge in drawable.edges}
    return nodes, edges


def _sse_payloads(events):
    return [json.loads(event.removeprefix("data: ").strip()) for event in events]


def test_runtime_topologies_and_checkpoints():
    """Freeze graph nodes, edges, and checkpoint ownership."""
    notebook_nodes, notebook_edges = _topology(notebook_chat_graph)
    assert notebook_nodes == {"__start__", "agent", "__end__"}
    assert notebook_edges == {
        ("__start__", "agent", False),
        ("agent", "__end__", False),
    }
    assert type(notebook_chat_graph.checkpointer).__name__ == "SqliteSaver"

    source_nodes, source_edges = _topology(source_chat_graph)
    assert source_nodes == {"__start__", "source_chat_agent", "__end__"}
    assert source_edges == {
        ("__start__", "source_chat_agent", False),
        ("source_chat_agent", "__end__", False),
    }
    assert type(source_chat_graph.checkpointer).__name__ == "SqliteSaver"

    ask_nodes, ask_edges = _topology(ask_graph)
    assert ask_nodes == {
        "__start__",
        "agent",
        "provide_answer",
        "write_final_answer",
        "__end__",
    }
    assert ask_edges == {
        ("__start__", "agent", False),
        ("agent", "provide_answer", True),
        ("provide_answer", "write_final_answer", False),
        ("write_final_answer", "__end__", False),
    }
    assert ask_graph.checkpointer is None


def test_notebook_chat_prompt_model_selection_and_cleaned_output():
    """Notebook Chat renders supplied context and invokes one synchronous model."""
    model = MagicMock()
    model.invoke.return_value = AIMessage(
        content="<think>not user-visible</think>Notebook answer"
    )
    provision = AsyncMock(return_value=model)
    state = {
        "messages": [HumanMessage(content="What changed?")],
        "notebook": SimpleNamespace(
            name="Runtime Research", description="Current behavior"
        ),
        "context": "source:alpha says the baseline is observable",
        "context_config": {"sources": {"alpha": "full content"}},
        "model_override": "model:session",
    }

    with patch("open_notebook.graphs.chat.provision_langchain_model", new=provision):
        result = call_model_with_messages(
            state, {"configurable": {"model_id": "model:request"}}
        )

    provision.assert_awaited_once()
    provision_args = provision.await_args
    assert provision_args.args[1:] == ("model:request", "chat")
    assert provision_args.kwargs == {"max_tokens": 8192}

    payload = model.invoke.call_args.args[0]
    assert [message.type for message in payload] == ["system", "human"]
    assert "Runtime Research" in payload[0].content
    assert "source:alpha says the baseline is observable" in payload[0].content
    assert result["messages"].content == "Notebook answer"


@pytest.mark.asyncio
async def test_notebook_chat_api_uses_mocked_db_checkpoint_and_session_model():
    """The API hydrates notebook/checkpoint state and persists the session touch."""
    old_message = HumanMessage(content="Earlier", id="message:old")
    ai_message = AIMessage(content="Current answer", id="message:new")
    session = SimpleNamespace(
        id="chat_session:session",
        title="Session",
        model_override="model:session",
        save=AsyncMock(),
    )
    graph = MagicMock()
    graph.get_state.return_value = SimpleNamespace(values={"messages": [old_message]})
    graph.invoke.return_value = {
        "messages": [
            old_message,
            HumanMessage(content="Now", id="message:user"),
            ai_message,
        ]
    }
    notebook = SimpleNamespace(id="notebook:research")

    with (
        patch(
            "api.routers._chat_shared.ChatSession.get",
            new=AsyncMock(return_value=session),
        ) as get_session,
        patch(
            "api.routers.chat.repo_query",
            new=AsyncMock(return_value=[{"out": "notebook:research"}]),
        ) as repo_query,
        patch(
            "api.routers.chat.Notebook.get",
            new=AsyncMock(return_value=notebook),
        ) as get_notebook,
        patch("api.routers.chat.chat_graph", new=graph),
    ):
        response = await execute_chat(
            ExecuteChatRequest(
                session_id="session",
                message="Now",
                context={"sources": [{"id": "source:alpha"}], "notes": []},
            )
        )

    get_session.assert_awaited_once_with("chat_session:session")
    repo_query.assert_awaited_once()
    get_notebook.assert_awaited_once_with("notebook:research")
    session.save.assert_awaited_once()

    invocation = graph.invoke.call_args.kwargs
    assert invocation["input"]["notebook"] is notebook
    assert invocation["input"]["context"]["sources"][0]["id"] == "source:alpha"
    assert invocation["input"]["messages"][-1].content == "Now"
    assert invocation["config"]["configurable"] == {
        "thread_id": "chat_session:session",
        "model_id": "model:session",
    }
    assert response.session_id == "session"
    assert [message.content for message in response.messages] == [
        "Earlier",
        "Now",
        "Current answer",
    ]


def test_source_chat_current_prompt_has_secondary_character_truncation():
    """Capture the pre-#1224 formatter behavior without endorsing it."""
    full_text = ("A" * 5_000) + "TAIL_NOT_IN_CURRENT_PROMPT"
    context_data = {
        "sources": [
            {
                "id": "source:alpha",
                "title": "Long source",
                "full_text": full_text,
            }
        ],
        "notes": [],
        "insights": [
            {
                "id": "source_insight:one",
                "source_id": "source:alpha",
                "insight_type": "summary",
                "content": "An insight",
            }
        ],
        "total_tokens": 1_300,
        "metadata": {"source_count": 1, "note_count": 0, "insight_count": 1},
    }
    model = MagicMock()
    model.invoke.return_value = AIMessage(content="Source answer")

    with (
        patch(
            "open_notebook.graphs.source_chat.build_source_context",
            new=AsyncMock(return_value=context_data),
        ) as build_context,
        patch(
            "open_notebook.graphs.source_chat.provision_langchain_model",
            new=AsyncMock(return_value=model),
        ) as provision,
    ):
        result = _call_model_with_source_context_inner(
            {
                "messages": [HumanMessage(content="Summarize")],
                "source_id": "source:alpha",
                "source": None,
                "insights": None,
                "context": None,
                "model_override": "model:source",
                "context_indicators": None,
            },
            {"configurable": {}},
        )

    build_context.assert_awaited_once_with(source_id="source:alpha", max_tokens=50_000)
    provision_args = provision.await_args
    assert provision_args.args[1:] == ("model:source", "chat")
    assert provision_args.kwargs == {"max_tokens": 8192}

    system_prompt = model.invoke.call_args.args[0][0].content
    assert "A" * 5_000 in system_prompt
    assert "TAIL_NOT_IN_CURRENT_PROMPT" not in system_prompt
    assert "[Content truncated]" in system_prompt
    assert result["context_indicators"] == {
        "sources": ["source:alpha"],
        "insights": ["source_insight:one"],
        "notes": [],
    }


@pytest.mark.asyncio
async def test_source_chat_current_builder_requests_short_context_without_full_text():
    """Capture the database-backed context gap described by issue #1224."""
    source = SimpleNamespace(id="source:alpha")

    async def get_context(*, context_size):
        if context_size == "long":
            return {
                "id": "source:alpha",
                "title": "Current baseline",
                "full_text": "Substantive source text",
            }
        return {"id": "source:alpha", "title": "Current baseline"}

    source.get_context = AsyncMock(side_effect=get_context)
    source.get_insights = AsyncMock(return_value=[])

    with patch(
        "open_notebook.utils.context_builder.Source.get",
        new=AsyncMock(return_value=source),
    ) as get_source:
        context_data = await build_source_context("alpha", max_tokens=50_000)

    get_source.assert_awaited_once_with("source:alpha")
    source.get_context.assert_awaited_once_with(context_size="short")
    assert context_data["sources"] == [
        {"id": "source:alpha", "title": "Current baseline"}
    ]
    assert "full_text" not in context_data["sources"][0]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Future Source Chat baseline from issue #1224: use full source text "
        "and one token budget, with no second formatter truncation"
    ),
)
@pytest.mark.asyncio
async def test_source_chat_issue_1224_future_baseline_includes_fitting_text_once():
    """Executable future contract; expected to xfail until #1224 is implemented."""
    full_text = ("B" * 6_000) + "END_OF_SOURCE"
    source = SimpleNamespace(id="source:alpha")

    async def get_context(*, context_size):
        if context_size == "long":
            return {
                "id": "source:alpha",
                "title": "Future baseline",
                "full_text": full_text,
            }
        return {"id": "source:alpha", "title": "Future baseline"}

    source.get_context = AsyncMock(side_effect=get_context)
    source.get_insights = AsyncMock(return_value=[])

    with patch(
        "open_notebook.utils.context_builder.Source.get",
        new=AsyncMock(return_value=source),
    ):
        context_data = await build_source_context("source:alpha", max_tokens=50_000)

    source.get_context.assert_awaited_once_with(context_size="long")
    assert context_data["sources"][0]["full_text"] == full_text
    formatted = _format_source_context(context_data)
    assert "END_OF_SOURCE" in formatted
    assert "[Content truncated]" not in formatted


@pytest.mark.asyncio
async def test_source_chat_sse_event_order_and_accumulated_ai_replay():
    """Source Chat emits the user event, all AI messages, indicators, then complete."""
    graph = MagicMock()
    graph.get_state.return_value = SimpleNamespace(
        values={"messages": [AIMessage(content="Earlier answer")]}
    )
    graph.invoke.return_value = {
        "messages": [
            AIMessage(content="Earlier answer"),
            HumanMessage(content="Next question"),
            AIMessage(content="New answer"),
        ],
        "context_indicators": {
            "sources": ["source:alpha"],
            "insights": [],
            "notes": [],
        },
    }

    with patch("api.routers.source_chat.source_chat_graph", new=graph):
        events = [
            event
            async for event in stream_source_chat_response(
                "chat_session:session",
                "source:alpha",
                "Next question",
                "model:source",
            )
        ]

    payloads = _sse_payloads(events)
    assert [payload["type"] for payload in payloads] == [
        "user_message",
        "ai_message",
        "ai_message",
        "context_indicators",
        "complete",
    ]
    assert [payloads[1]["content"], payloads[2]["content"]] == [
        "Earlier answer",
        "New answer",
    ]
    assert graph.invoke.call_args.kwargs["config"]["configurable"] == {
        "thread_id": "chat_session:session",
        "model_id": "model:source",
    }


@pytest.mark.asyncio
async def test_ask_graph_fanout_search_and_three_mocked_models():
    """ASK plans, searches the mocked database, answers, and synthesizes."""
    strategy_model = MagicMock()
    strategy_model.ainvoke = AsyncMock(
        return_value=AIMessage(
            content=(
                '{"reasoning":"Find the runtime baseline",'
                '"searches":[{"term":"runtime baseline",'
                '"instructions":"Extract the persisted state"}]}'
            )
        )
    )
    answer_model = MagicMock()
    answer_model.ainvoke = AsyncMock(
        return_value=AIMessage(content="The state is checkpointed [note:one].")
    )
    final_model = MagicMock()
    final_model.ainvoke = AsyncMock(
        return_value=AIMessage(content="Final synthesis [note:one].")
    )
    provision = AsyncMock(side_effect=[strategy_model, answer_model, final_model])
    vector_search = AsyncMock(
        return_value=[
            {
                "id": "note:one",
                "title": "Runtime note",
                "content": "Checkpoint details",
                "score": 0.9,
            }
        ]
    )

    with (
        patch("open_notebook.graphs.ask.provision_langchain_model", new=provision),
        patch("open_notebook.graphs.ask.vector_search", new=vector_search),
    ):
        result = await ask_graph.ainvoke(
            {"question": "How is runtime state stored?"},
            config={
                "configurable": {
                    "strategy_model": "model:strategy",
                    "answer_model": "model:answer",
                    "final_answer_model": "model:final",
                }
            },
        )

    vector_search.assert_awaited_once_with("runtime baseline", 10, True, True)
    assert [item.args[1:3] for item in provision.await_args_list] == [
        ("model:strategy", "tools"),
        ("model:answer", "tools"),
        ("model:final", "tools"),
    ]
    assert provision.await_args_list[0].kwargs == {
        "max_tokens": 2000,
        "structured": {"type": "json"},
    }
    assert provision.await_args_list[1].kwargs == {"max_tokens": 2000}
    assert provision.await_args_list[2].kwargs == {"max_tokens": 2000}
    assert result["strategy"].reasoning == "Find the runtime baseline"
    assert result["answers"] == ["The state is checkpointed [note:one]."]
    assert result["final_answer"] == "Final synthesis [note:one]."


@pytest.mark.asyncio
async def test_ask_sse_event_contract():
    """The streaming adapter exposes graph updates and a terminal summary."""

    class FakeAskGraph:
        def astream(self, **kwargs):
            self.kwargs = kwargs

            async def chunks():
                yield {
                    "agent": {
                        "strategy": SimpleNamespace(
                            reasoning="Search once",
                            searches=[
                                SimpleNamespace(
                                    term="checkpoint", instructions="Explain it"
                                )
                            ],
                        )
                    }
                }
                yield {"provide_answer": {"answers": ["Partial [note:one]."]}}
                yield {"write_final_answer": {"final_answer": "Complete [note:one]."}}

            return chunks()

    graph = FakeAskGraph()
    models = [
        SimpleNamespace(id="model:strategy"),
        SimpleNamespace(id="model:answer"),
        SimpleNamespace(id="model:final"),
    ]

    with patch("api.routers.search.ask_graph", new=graph):
        events = [
            event
            async for event in stream_ask_response("What is checkpointing?", *models)
        ]

    payloads = _sse_payloads(events)
    assert [payload["type"] for payload in payloads] == [
        "strategy",
        "answer",
        "final_answer",
        "complete",
    ]
    assert payloads[-1]["final_answer"] == "Complete [note:one]."
    assert graph.kwargs == {
        "input": {"question": "What is checkpointing?"},
        "config": {
            "configurable": {
                "strategy_model": "model:strategy",
                "answer_model": "model:answer",
                "final_answer_model": "model:final",
            }
        },
        "stream_mode": "updates",
    }
