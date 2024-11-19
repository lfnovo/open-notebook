from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from loguru import logger
from typing_extensions import TypedDict

from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.prompter import Prompter


class PatternChainState(TypedDict):
    prompt: str
    parser: Optional[Any]
    input_text: str
    output: str


def call_model(state: dict, config: RunnableConfig) -> dict:
    content = state["input_text"]
    system_prompt = Prompter(
        prompt_text=state["prompt"], parser=state.get("parser")
    ).render(data=state)
    logger.warning(content)
    payload = [SystemMessage(content=system_prompt)] + [HumanMessage(content=content)]
    chain = provision_langchain_model(
        str(payload),
        config.get("configurable", {}).get("model_id"),
        "transformation",
        max_tokens=5000,
    )

    response = chain.invoke(payload)

    return {"output": response.content}


agent_state = StateGraph(PatternChainState)
agent_state.add_node("agent", call_model)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)

graph = agent_state.compile()
