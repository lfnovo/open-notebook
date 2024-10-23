import os

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.graphs.utils import run_pattern


class PatternState(TypedDict):
    input_text: str
    pattern: str
    output: str


def call_model(state: dict, config: RunnableConfig) -> dict:
    model_name = config.get("configurable", {}).get(
        "model_name", os.environ.get("DEFAULT_MODEL")
    )
    return {
        "output": run_pattern(
            pattern_name=state["pattern"],
            model_name=model_name,
            state=state,
        )
    }


agent_state = StateGraph(PatternState)
agent_state.add_node("agent", call_model)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
