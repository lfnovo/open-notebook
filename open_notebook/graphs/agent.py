"""
Research Agent for Open Notebook
A ReAct-style agent that can search, analyze, and create notes.
"""

import os
from typing import Annotated, Any, Dict, List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from loguru import logger
from typing_extensions import TypedDict
from esperanto import DeepSeekLanguageModel, OpenAICompatibleLanguageModel

from open_notebook.graphs.agent_tools import AGENT_TOOLS


class AgentState(TypedDict):
    """State for the research agent."""
    messages: Annotated[list, add_messages]
    notebook_id: Optional[str]
    task: Optional[str]
    api_key: Optional[str]
    model_override: Optional[str]
    tool_history: List[Dict[str, Any]]


# Supported models
SUPPORTED_MODELS = {
    "deepseek-chat": {
        "provider": "deepseek",
        "model_name": "deepseek-chat",
        "description": "DeepSeek Chat - Cost effective"
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "model_name": "deepseek-reasoner", 
        "description": "DeepSeek Reasoner - Advanced reasoning"
    },
    "qwen-plus": {
        "provider": "qwen",
        "model_name": "qwen-plus",
        "description": "Qwen Plus"
    },
    "qwen-turbo": {
        "provider": "qwen",
        "model_name": "qwen-turbo",
        "description": "Qwen Turbo"
    },
}


AGENT_SYSTEM_PROMPT = """You are a Research Assistant. Help users search their knowledge base and organize notes.

Available tools:
- search_knowledge_base: Search sources and notes
- get_source_content: Get full source content  
- create_note: Create a new note
- list_notebook_sources: List all sources
- list_notebook_notes: List all notes

Current context: {context}

Be helpful and concise. Use tools when needed.
"""


def get_agent_model(model_name: str, api_key: Optional[str] = None):
    """Get a LangChain model for the agent."""
    model_config = SUPPORTED_MODELS.get(model_name, SUPPORTED_MODELS["deepseek-chat"])
    provider = model_config["provider"]
    
    if provider == "deepseek":
        final_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not final_api_key:
            raise ValueError("DeepSeek API key required. Set DEEPSEEK_API_KEY environment variable.")
        
        model = DeepSeekLanguageModel(
            model_name=model_config["model_name"],
            api_key=final_api_key,
        )
        return model.to_langchain()
    
    elif provider == "qwen":
        final_api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_COMPATIBLE_API_KEY_LLM")
        if not final_api_key:
            raise ValueError("Qwen API key required.")
        
        model = OpenAICompatibleLanguageModel(
            model_name=model_config["model_name"],
            api_key=final_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return model.to_langchain()
    
    raise ValueError(f"Unsupported provider: {provider}")


async def agent_node(state: AgentState, config: RunnableConfig) -> dict:
    """Main agent node."""
    messages = state.get("messages", [])
    notebook_id = state.get("notebook_id")
    api_key = state.get("api_key")
    model_override = state.get("model_override", "deepseek-chat")
    
    context = f"Notebook: {notebook_id}" if notebook_id else "No notebook selected"
    system_prompt = AGENT_SYSTEM_PROMPT.format(context=context)
    full_messages = [SystemMessage(content=system_prompt)] + messages
    
    # Get model name
    model_name = config.get("configurable", {}).get("model_id") or model_override or "deepseek-chat"
    if "/" in model_name:
        model_name = model_name.split("/")[-1]
    
    logger.info(f"Agent using model: {model_name}")
    
    model = get_agent_model(model_name, api_key)
    model_with_tools = model.bind_tools(AGENT_TOOLS)
    
    response = await model_with_tools.ainvoke(full_messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine next step."""
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


def create_tool_node():
    """Create tool execution node."""
    return ToolNode(AGENT_TOOLS)


def create_agent_graph():
    """Create and compile the agent graph."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", create_tool_node())
    
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


agent_graph = create_agent_graph()


async def run_agent(
    message: str,
    thread_id: str,
    notebook_id: Optional[str] = None,
    api_key: Optional[str] = None,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Run agent with a message."""
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "notebook_id": notebook_id,
        "api_key": api_key,
        "model_override": model_override or "deepseek-chat",
        "tool_history": [],
    }
    
    config = RunnableConfig(configurable={"thread_id": thread_id, "model_id": model_override})
    return await agent_graph.ainvoke(initial_state, config)


async def stream_agent(
    message: str,
    thread_id: str,
    notebook_id: Optional[str] = None,
    api_key: Optional[str] = None,
    model_override: Optional[str] = None,
):
    """Stream agent execution."""
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "notebook_id": notebook_id,
        "api_key": api_key,
        "model_override": model_override or "deepseek-chat",
        "tool_history": [],
    }
    
    config = RunnableConfig(configurable={"thread_id": thread_id, "model_id": model_override})
    
    async for event in agent_graph.astream_events(initial_state, config, version="v2"):
        kind = event.get("event")
        
        if kind == "on_chat_model_start":
            yield {"type": "thinking", "content": "Thinking..."}
        elif kind == "on_tool_start":
            yield {"type": "tool_call", "tool": event.get("name", ""), "input": event.get("data", {}).get("input", {})}
        elif kind == "on_tool_end":
            yield {"type": "tool_result", "tool": event.get("name", ""), "output": str(event.get("data", {}).get("output", ""))[:500]}
        elif kind == "on_chat_model_end":
            output = event.get("data", {}).get("output")
            if output and hasattr(output, "content"):
                if not (hasattr(output, "tool_calls") and output.tool_calls):
                    yield {"type": "response", "content": output.content}
