import os

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.domain import Note, Notebook, Source
from open_notebook.graphs.utils import run_pattern


class DocQueryState(TypedDict):
    doc_id: str
    doc_content: str
    question: str
    answer: str
    notebook: Notebook


def call_model(state: dict, config: RunnableConfig) -> dict:
    model_name = config.get("configurable", {}).get(
        "model_name", os.environ.get("RETRIEVAL_MODEL")
    )
    return {"answer": run_pattern("doc_query", model_name, state)}


# todo: there is probably a better way to do this and avoid repetition
def get_content(state: DocQueryState) -> dict:
    doc_id = state["doc_id"]
    if "note:" in doc_id:
        doc: Note = Note.get(id=doc_id)
    elif "source:" in doc_id:
        doc: Source = Source.get(id=doc_id)
    doc_content = doc.get_context("long") if doc else None
    return {"doc_content": doc_content}


agent_state = StateGraph(DocQueryState)
agent_state.add_node("get_content", get_content)
agent_state.add_node("agent", call_model)
agent_state.add_edge(START, "get_content")
agent_state.add_edge("get_content", "agent")
agent_state.add_edge("agent", END)

graph = agent_state.compile()
