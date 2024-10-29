import operator
import os
from typing import List, Literal, Sequence

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

from open_notebook.graphs.utils import run_pattern


class PatternChainState(TypedDict):
    content_stack: Annotated[Sequence[str], operator.add]
    transformations: List[str]
    output: str


def call_model(state: dict, config: RunnableConfig) -> dict:
    model_name = config.get("configurable", {}).get(
        "model_name", os.environ.get("DEFAULT_MODEL")
    )
    transformations = state["transformations"]
    current_transformation = transformations.pop(0)
    if current_transformation.startswith("patterns/"):
        input_args = {"input_text": state["content_stack"][-1]}
    else:
        input_args = {
            "input_text": state["content_stack"][-1],
            "command": current_transformation,
        }
        current_transformation = "patterns/custom"

    transformation_result = run_pattern(
        pattern_name=current_transformation,
        model_name=model_name,
        state=input_args,
    )
    return {
        "content_stack": [transformation_result.content],
        "output": transformation_result.content,
        "transformations": state["transformations"],
    }


def transform_condition(state: PatternChainState) -> Literal["agent", END]:  # type: ignore
    """
    Checks whether there are more chunks to process.
    """
    if len(state["transformations"]) > 0:
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
