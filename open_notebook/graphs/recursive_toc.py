import os
from typing import List, Literal

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.config import DEFAULT_MODELS
from open_notebook.graphs.utils import run_pattern
from open_notebook.utils import split_text


class TocState(TypedDict):
    chunks: List[str]
    content: str
    toc: str


def build_chunks(state: TocState) -> dict:
    """
    Split the input text into chunks.
    """
    return {
        "chunks": split_text(
            state["content"],
            chunk=int(os.environ.get("SUMMARY_CHUNK_SIZE", 200000)),
            overlap=int(os.environ.get("SUMMARY_CHUNK_OVERLAP", 1000)),
        )
    }


def setup_next_chunk(state: TocState) -> dict:
    """
    Move the next item in the chunk to the processing area
    """
    state["content"] = state["chunks"].pop(0)
    return {"chunks": state["chunks"], "content": state["content"]}


def chunk_condition(state: TocState) -> Literal["get_chunk", END]:  # type: ignore
    """
    Checks whether there are more chunks to process.
    """
    if len(state["chunks"]) > 0:
        return "get_chunk"
    return END


def call_model(state: TocState, config: RunnableConfig) -> dict:
    model_id = config.get("configurable", {}).get(
        "model_id", DEFAULT_MODELS.default_transformation_model
    )
    return {
        "toc": run_pattern(
            pattern_name="recursive_toc",
            model_id=model_id,
            state=state,
        ).content
    }


agent_state = StateGraph(TocState)
agent_state.add_node("setup_chunk", build_chunks)
agent_state.add_edge(START, "setup_chunk")
agent_state.add_conditional_edges(
    "setup_chunk",
    chunk_condition,
)
agent_state.add_node("get_chunk", setup_next_chunk)
agent_state.add_node("agent", call_model)
agent_state.add_edge("get_chunk", "agent")
agent_state.add_conditional_edges(
    "agent",
    chunk_condition,
)

graph = agent_state.compile()
