from typing import Annotated

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from open_notebook.graphs.tools import repository_search
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.prompter import Prompter

tools = [repository_search]
tool_node = ToolNode(tools)


class ThreadState(TypedDict):
    messages: Annotated[list, add_messages]
    # notebook: Optional[Notebook]
    # context: Optional[str]
    # context_config: Optional[dict]


def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    system_prompt = Prompter(prompt_template="rag").render(data=state)
    payload = [system_prompt] + state.get("messages", [])
    model = provision_langchain_model(str(payload), config, "tools", max_tokens=2000)
    model = model.bind_tools(tools)
    ai_message = model.invoke(payload)
    return {"messages": ai_message}


agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("tools", tool_node)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges(
    "agent",
    tools_condition,
)
agent_state.add_edge("tools", "agent")
graph = agent_state.compile()
