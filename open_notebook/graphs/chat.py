import os
import sqlite3
from typing import Annotated, Optional

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_notebook.domain import Notebook
from open_notebook.graphs.utils import run_pattern


class ThreadState(TypedDict):
    messages: Annotated[list, add_messages]
    notebook: Optional[Notebook]
    context: Optional[str]
    context_config: Optional[dict]


def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    model_name = config.get("configurable", {}).get("model_name", None)
    ai_message = run_pattern(
        "chat",
        model_name,
        messages=state["messages"],
        state=state,
    )
    return {"messages": ai_message}


conn = sqlite3.connect(
    os.environ.get("CHECKPOINT_DATA_PATH", "sqlite-db/checkpoints.sqlite"),
    check_same_thread=False,
)
memory = SqliteSaver(conn)

agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile(checkpointer=memory)
