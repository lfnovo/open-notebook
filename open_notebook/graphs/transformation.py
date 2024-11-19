from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.prompter import Prompter


class TransformationState(TypedDict):
    input_text: str
    source: Source
    transformation: Transformation
    output: str


def run_transformation(state: dict, config: RunnableConfig) -> dict:
    source: Source = state.get("source")
    content = state.get("input_text")
    assert source or content, "No content to transform"
    transformation: Transformation = state["transformation"]
    if not content:
        content = source.full_text
    transformation_prompt_text = transformation.prompt
    default_prompts: DefaultPrompts = DefaultPrompts()
    if default_prompts.transformation_instructions:
        transformation_prompt_text = f"{default_prompts.transformation_instructions}\n\n{transformation_prompt_text}"

    transformation_prompt_text = f"{transformation_prompt_text}\n\n# INPUT"

    system_prompt = Prompter(prompt_text=transformation_prompt_text).render(data=state)
    payload = [SystemMessage(content=system_prompt)] + [HumanMessage(content=content)]
    chain = provision_langchain_model(
        str(payload),
        config.get("configurable", {}).get("model_id"),
        "transformation",
        max_tokens=5000,
    )

    response = chain.invoke(payload)
    if source:
        source.add_insight(transformation.title, response.content)

    return {
        "output": response.content,
    }


agent_state = StateGraph(TransformationState)
agent_state.add_node("agent", run_transformation)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
