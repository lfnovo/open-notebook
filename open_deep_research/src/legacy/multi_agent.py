from typing import List, Annotated, TypedDict, Literal, cast
from pydantic import BaseModel, Field
import operator
import warnings

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool, BaseTool
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import MessagesState

from langgraph.types import Command, Send
from langgraph.graph import START, END, StateGraph

from legacy.configuration import MultiAgentConfiguration
from legacy.utils import (
    get_config_value,
    tavily_search,
    duckduckgo_search,
    get_today_str,
)

from legacy.prompts import SUPERVISOR_INSTRUCTIONS, RESEARCH_INSTRUCTIONS

## Tools factory - will be initialized based on configuration
def get_search_tool(config: RunnableConfig):
    """Get the appropriate search tool based on configuration"""
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    search_api = get_config_value(configurable.search_api)

    # Return None if no search tool is requested
    if search_api.lower() == "none":
        return None

    # TODO: Configure other search functions as tools
    if search_api.lower() == "tavily":
        search_tool = tavily_search
    elif search_api.lower() == "duckduckgo":
        search_tool = duckduckgo_search
    else:
        raise NotImplementedError(
            f"The search API '{search_api}' is not yet supported in the multi-agent implementation. "
            f"Currently, only Tavily/DuckDuckGo/None is supported. Please use the graph-based implementation in "
            f"src/open_deep_research/graph.py for other search APIs, or set search_api to 'tavily', 'duckduckgo', or 'none'."
        )

    tool_metadata = {**(search_tool.metadata or {}), "type": "search"}
    search_tool.metadata = tool_metadata
    return search_tool

class Section(BaseModel):
    """Section of the report."""
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Research scope for this section of the report.",
    )
    content: str = Field(
        description="The content of the section."
    )

class Sections(BaseModel):
    """List of section titles of the report."""
    sections: List[str] = Field(
        description="Sections of the report.",
    )

class Introduction(BaseModel):
    """Introduction to the report."""
    name: str = Field(
        description="Name for the report.",
    )
    content: str = Field(
        description="The content of the introduction, giving an overview of the report."
    )

class Conclusion(BaseModel):
    """Conclusion to the report."""
    name: str = Field(
        description="Name for the conclusion of the report.",
    )
    content: str = Field(
        description="The content of the conclusion, summarizing the report."
    )

class Question(BaseModel):
    """Ask a follow-up question to clarify the report scope."""
    question: str = Field(
        description="A specific question to ask the user to clarify the scope, focus, or requirements of the report."
    )

# No-op tool to indicate that the research is complete
class FinishResearch(BaseModel):
    """Finish the research."""

# No-op tool to indicate that the report writing is complete
class FinishReport(BaseModel):
    """Finish the report."""

## State
class ReportStateOutput(MessagesState):
    final_report: str # Final report
    # for evaluation purposes only
    # this is included only if configurable.include_source_str is True
    source_str: str # String of formatted source content from web search

class ReportState(MessagesState):
    sections: list[str] # List of report sections 
    completed_sections: Annotated[list[Section], operator.add] # Send() API key
    final_report: str # Final report
    # for evaluation purposes only
    # this is included only if configurable.include_source_str is True
    source_str: Annotated[str, operator.add] # String of formatted source content from web search

class SectionState(MessagesState):
    section: str # Report section  
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API
    # for evaluation purposes only
    # this is included only if configurable.include_source_str is True
    source_str: str # String of formatted source content from web search

class SectionOutputState(TypedDict):
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API
    # for evaluation purposes only
    # this is included only if configurable.include_source_str is True
    source_str: str # String of formatted source content from web search


async def _load_mcp_tools(
    config: RunnableConfig,
    existing_tool_names: set[str],
) -> list[BaseTool]:
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    if not configurable.mcp_server_config:
        return []

    mcp_server_config = configurable.mcp_server_config
    client = MultiServerMCPClient(mcp_server_config)
    mcp_tools = await client.get_tools()
    filtered_mcp_tools: list[BaseTool] = []
    for tool in mcp_tools:
        # TODO: this will likely be hard to manage
        # on a remote server that's not controlled by the developer
        # best solution here is allowing tool name prefixes in MultiServerMCPClient
        if tool.name in existing_tool_names:
            warnings.warn(
                f"Trying to add MCP tool with a name {tool.name} that is already in use - this tool will be ignored."
            )
            continue

        if configurable.mcp_tools_to_include and tool.name not in configurable.mcp_tools_to_include:
            continue

        filtered_mcp_tools.append(tool)

    return filtered_mcp_tools


# Tool lists will be built dynamically based on configuration
async def get_supervisor_tools(config: RunnableConfig) -> list[BaseTool]:
    """Get supervisor tools based on configuration"""
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    search_tool = get_search_tool(config)
    tools = [tool(Sections), tool(Introduction), tool(Conclusion), tool(FinishReport)]
    if configurable.ask_for_clarification:
        tools.append(tool(Question))
    if search_tool is not None:
        tools.append(search_tool)  # Add search tool, if available
    existing_tool_names = {cast(BaseTool, tool).name for tool in tools}
    mcp_tools = await _load_mcp_tools(config, existing_tool_names)
    tools.extend(mcp_tools)
    return tools


async def get_research_tools(config: RunnableConfig) -> list[BaseTool]:
    """Get research tools based on configuration"""
    search_tool = get_search_tool(config)
    tools = [tool(Section), tool(FinishResearch)]
    if search_tool is not None:
        tools.append(search_tool)  # Add search tool, if available
    existing_tool_names = {cast(BaseTool, tool).name for tool in tools}
    mcp_tools = await _load_mcp_tools(config, existing_tool_names)
    tools.extend(mcp_tools)
    return tools


async def supervisor(state: ReportState, config: RunnableConfig):
    """LLM decides whether to call a tool or not"""

    # Messages
    messages = state["messages"]

    # Get configuration
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    supervisor_model = get_config_value(configurable.supervisor_model)

    # Initialize the model
    llm = init_chat_model(model=supervisor_model)
    
    # If sections have been completed, but we don't yet have the final report, then we need to initiate writing the introduction and conclusion
    if state.get("completed_sections") and not state.get("final_report"):
        research_complete_message = {"role": "user", "content": "Research is complete. Now write the introduction and conclusion for the report. Here are the completed main body sections: \n\n" + "\n\n".join([s.content for s in state["completed_sections"]])}
        messages = messages + [research_complete_message]

    # Get tools based on configuration
    supervisor_tool_list = await get_supervisor_tools(config)
    
    
    llm_with_tools = (
        llm
        .bind_tools(
            supervisor_tool_list,
            parallel_tool_calls=False,
            # force at least one tool call
            tool_choice="any"
        )
    )

    # Get system prompt
    system_prompt = SUPERVISOR_INSTRUCTIONS.format(today=get_today_str())
    if configurable.mcp_prompt:
        system_prompt += f"\n\n{configurable.mcp_prompt}"

    # Invoke
    return {
        "messages": [
            await llm_with_tools.ainvoke(
                [
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ]
                + messages
            )
        ]
    }

async def supervisor_tools(state: ReportState, config: RunnableConfig)  -> Command[Literal["supervisor", "research_team", "__end__"]]:
    """Performs the tool call and sends to the research agent"""
    configurable = MultiAgentConfiguration.from_runnable_config(config)

    result = []
    sections_list = []
    intro_content = None
    conclusion_content = None
    source_str = ""

    # Get tools based on configuration
    supervisor_tool_list = await get_supervisor_tools(config)
    supervisor_tools_by_name = {tool.name: tool for tool in supervisor_tool_list}
    search_tool_names = {
        tool.name
        for tool in supervisor_tool_list
        if tool.metadata is not None and tool.metadata.get("type") == "search"
    }

    # First process all tool calls to ensure we respond to each one (required for OpenAI)
    for tool_call in state["messages"][-1].tool_calls:
        # Get the tool
        tool = supervisor_tools_by_name[tool_call["name"]]
        # Perform the tool call - use ainvoke for async tools
        try:
            observation = await tool.ainvoke(tool_call["args"], config)
        except NotImplementedError:
            observation = tool.invoke(tool_call["args"], config)

        # Append to messages 
        result.append({"role": "tool", 
                       "content": observation, 
                       "name": tool_call["name"], 
                       "tool_call_id": tool_call["id"]})
        
        # Store special tool results for processing after all tools have been called
        if tool_call["name"] == "Question":
            # Question tool was called - return to supervisor to ask the question
            question_obj = cast(Question, observation)
            result.append({"role": "assistant", "content": question_obj.question})
            return Command(goto=END, update={"messages": result})
        elif tool_call["name"] == "FinishReport":
            result.append({"role": "user", "content": "Report is Finish"})
            return Command(goto=END, update={"messages": result})
        elif tool_call["name"] == "Sections":
            sections_list = cast(Sections, observation).sections
        elif tool_call["name"] == "Introduction":
            # Format introduction with proper H1 heading if not already formatted
            observation = cast(Introduction, observation)
            if not observation.content.startswith("# "):
                intro_content = f"# {observation.name}\n\n{observation.content}"
            else:
                intro_content = observation.content
        elif tool_call["name"] == "Conclusion":
            # Format conclusion with proper H2 heading if not already formatted
            observation = cast(Conclusion, observation)
            if not observation.content.startswith("## "):
                conclusion_content = f"## {observation.name}\n\n{observation.content}"
            else:
                conclusion_content = observation.content
        elif tool_call["name"] in search_tool_names and configurable.include_source_str:
            source_str += cast(str, observation)

    # After processing all tool calls, decide what to do next
    if sections_list:
        # Send the sections to the research agents
        return Command(goto=[Send("research_team", {"section": s}) for s in sections_list], update={"messages": result})
    elif intro_content:
        # Store introduction while waiting for conclusion
        # Append to messages to guide the LLM to write conclusion next
        result.append({"role": "user", "content": "Introduction written. Now write a conclusion section."})
        state_update = {
            "final_report": intro_content,
            "messages": result,
        }
    elif conclusion_content:
        # Get all sections and combine in proper order: Introduction, Body Sections, Conclusion
        intro = state.get("final_report", "")
        body_sections = "\n\n".join([s.content for s in state["completed_sections"]])
        
        # Assemble final report in correct order
        complete_report = f"{intro}\n\n{body_sections}\n\n{conclusion_content}"
        
        # Append to messages to indicate completion
        result.append({"role": "user", "content": "Report is now complete with introduction, body sections, and conclusion."})

        state_update = {
            "final_report": complete_report,
            "messages": result,
        }
    else:
        # Default case (for search tools, etc.)
        state_update = {"messages": result}

    # Include source string for evaluation
    if configurable.include_source_str and source_str:
        state_update["source_str"] = source_str

    return Command(goto="supervisor", update=state_update)

async def supervisor_should_continue(state: ReportState) -> str:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]
    # End because the supervisor asked a question or is finished
    if not last_message.tool_calls:
        # Exit the graph
        return END

    # If the LLM makes a tool call, then perform an action
    return "supervisor_tools"

async def research_agent(state: SectionState, config: RunnableConfig):
    """LLM decides whether to call a tool or not"""
    
    # Get configuration
    configurable = MultiAgentConfiguration.from_runnable_config(config)
    researcher_model = get_config_value(configurable.researcher_model)
    
    # Initialize the model
    llm = init_chat_model(model=researcher_model)

    # Get tools based on configuration
    research_tool_list = await get_research_tools(config)
    system_prompt = RESEARCH_INSTRUCTIONS.format(
        section_description=state["section"],
        number_of_queries=configurable.number_of_queries,
        today=get_today_str(),
    )
    if configurable.mcp_prompt:
        system_prompt += f"\n\n{configurable.mcp_prompt}"

    # Ensure we have at least one user message (required by Anthropic)
    messages = state.get("messages", [])
    if not messages:
        messages = [{"role": "user", "content": f"Please research and write the section: {state['section']}"}]

    return {
        "messages": [
            # Enforce tool calling to either perform more search or call the Section tool to write the section
            await llm.bind_tools(research_tool_list,             
                                 parallel_tool_calls=False,
                                 # force at least one tool call
                                 tool_choice="any").ainvoke(
                [
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ]
                + messages
            )
        ]
    }

async def research_agent_tools(state: SectionState, config: RunnableConfig):
    """Performs the tool call and route to supervisor or continue the research loop"""
    configurable = MultiAgentConfiguration.from_runnable_config(config)

    result = []
    completed_section = None
    source_str = ""
    
    # Get tools based on configuration
    research_tool_list = await get_research_tools(config)
    research_tools_by_name = {tool.name: tool for tool in research_tool_list}
    search_tool_names = {
        tool.name
        for tool in research_tool_list
        if tool.metadata is not None and tool.metadata.get("type") == "search"
    }
    
    # Process all tool calls first (required for OpenAI)
    for tool_call in state["messages"][-1].tool_calls:
        # Get the tool
        tool = research_tools_by_name[tool_call["name"]]
        # Perform the tool call - use ainvoke for async tools
        try:
            observation = await tool.ainvoke(tool_call["args"], config)
        except NotImplementedError:
            observation = tool.invoke(tool_call["args"], config)

        # Append to messages 
        result.append({"role": "tool", 
                       "content": observation, 
                       "name": tool_call["name"], 
                       "tool_call_id": tool_call["id"]})
        
        # Store the section observation if a Section tool was called
        if tool_call["name"] == "Section":
            completed_section = cast(Section, observation)

        # Store the source string if a search tool was called
        if tool_call["name"] in search_tool_names and configurable.include_source_str:
            source_str += cast(str, observation)
    
    # After processing all tools, decide what to do next
    state_update = {"messages": result}
    if completed_section:
        # Write the completed section to state and return to the supervisor
        state_update["completed_sections"] = [completed_section]
    if configurable.include_source_str and source_str:
        state_update["source_str"] = source_str

    return state_update

async def research_agent_should_continue(state: SectionState) -> str:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls[0]["name"] == "FinishResearch":
        # Research is done - return to supervisor
        return END
    else:
        return "research_agent_tools"
    
"""Build the multi-agent workflow"""

# Research agent workflow
research_builder = StateGraph(SectionState, output=SectionOutputState, config_schema=MultiAgentConfiguration)
research_builder.add_node("research_agent", research_agent)
research_builder.add_node("research_agent_tools", research_agent_tools)
research_builder.add_edge(START, "research_agent") 
research_builder.add_conditional_edges(
    "research_agent",
    research_agent_should_continue,
    ["research_agent_tools", END]
)
research_builder.add_edge("research_agent_tools", "research_agent")

# Supervisor workflow
supervisor_builder = StateGraph(ReportState, input=MessagesState, output=ReportStateOutput, config_schema=MultiAgentConfiguration)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_node("research_team", research_builder.compile())

# Flow of the supervisor agent
supervisor_builder.add_edge(START, "supervisor")
supervisor_builder.add_conditional_edges(
    "supervisor",
    supervisor_should_continue,
    ["supervisor_tools", END]
)
supervisor_builder.add_edge("research_team", "supervisor")

graph = supervisor_builder.compile()