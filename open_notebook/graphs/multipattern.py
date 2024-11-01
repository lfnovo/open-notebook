import operator
from typing import List, Literal, Sequence

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

from open_notebook.domain.models import DefaultModels
from open_notebook.graphs.utils import run_pattern

DEFAULT_MODELS = DefaultModels.load()


class PatternChainState(TypedDict):
    content_stack: Annotated[Sequence[str], operator.add]
    patterns: List[str]
    output: str


def call_model(state: dict, config: RunnableConfig) -> dict:
    model_id = config.get("configurable", {}).get(
        "model_id", DEFAULT_MODELS.default_transformation_model
    )
    patterns = state["patterns"]
    current_transformation = patterns.pop(0)
    if current_transformation.startswith("patterns/"):
        input_args = {"input_text": state["content_stack"][-1]}
    else:
        input_args = {
            "input_text": state["content_stack"][-1],
            "command": current_transformation,
        }
        current_transformation = "patterns/default/command"

    transformation_result = run_pattern(
        pattern_name=current_transformation,
        model_id=model_id,
        state=input_args,
    )
    return {
        "content_stack": [transformation_result.content],
        "output": transformation_result.content,
        "patterns": state["patterns"],
    }


def transform_condition(state: PatternChainState) -> Literal["agent", END]:  # type: ignore
    """
    Checks whether there are more chunks to process.
    """
    if len(state["patterns"]) > 0:
        return "agent"
    return END


agent_state = StateGraph(PatternChainState)
agent_state.add_node("agent", call_model)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges(
    "agent",
    transform_condition,
)
graph = agent_state.compile()
