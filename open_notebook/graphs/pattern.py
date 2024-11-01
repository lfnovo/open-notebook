from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.config import load_default_models
from open_notebook.graphs.utils import run_pattern

DEFAULT_MODELS, EMBEDDING_MODEL, SPEECH_TO_TEXT_MODEL = load_default_models()


class PatternState(TypedDict):
    input_text: str
    pattern: str
    output: str


def call_model(state: dict, config: RunnableConfig) -> dict:
    model_id = config.get("configurable", {}).get(
        "model_id", DEFAULT_MODELS.default_transformation_model
    )
    return {
        "output": run_pattern(
            pattern_name=state["pattern"],
            model_id=model_id,
            state=state,
        )
    }


agent_state = StateGraph(PatternState)
agent_state.add_node("agent", call_model)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
