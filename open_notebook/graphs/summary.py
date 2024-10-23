import os
from typing import List, Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from open_notebook.graphs.utils import run_pattern
from open_notebook.utils import split_text


class SummaryResponse(BaseModel):
    """This is schema of your response. Please provide a JSON object with the enclosed keys"""

    summary: str
    topics: List[str]
    title: str


class SummaryState(TypedDict):
    chunks: List[str]
    content: str
    output: SummaryResponse


def build_chunks(state: SummaryState) -> dict:
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


def setup_next_chunk(state: SummaryState) -> dict:
    """
    Move the next item in the chunk to the processing area
    """
    state["content"] = state["chunks"].pop(0)
    return {"chunks": state["chunks"], "content": state["content"]}


def chunk_condition(state: SummaryState) -> Literal["get_chunk", END]:  # type: ignore
    """
    Checks whether there are more chunks to process.
    """
    if len(state["chunks"]) > 0:
        return "get_chunk"
    return END


def call_model(state: SummaryState, config: RunnableConfig) -> dict:
    model_name = config.get("configurable", {}).get(
        "model_name", os.environ.get("SUMMARIZATION_MODEL")
    )
    parser = PydanticOutputParser(pydantic_object=SummaryResponse)
    return {
        "output": run_pattern(
            pattern_name="summarize",
            model_name=model_name,
            state=state,
            parser=parser,
        )
    }


agent_state = StateGraph(SummaryState)
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
