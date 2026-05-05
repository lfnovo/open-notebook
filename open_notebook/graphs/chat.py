import asyncio
from typing import Annotated, Optional

from ai_prompter import Prompter
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content


class ThreadState(TypedDict):
    messages: Annotated[list, add_messages]
    notebook: Optional[Notebook]
    context: Optional[str]
    context_config: Optional[dict]
    model_override: Optional[str]
    enable_web_search: Optional[bool]


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        system_prompt = Prompter(prompt_template="chat/system").render(data=state)  # type: ignore[arg-type]
        payload = [SystemMessage(content=system_prompt)] + state.get("messages", [])
        model_id = config.get("configurable", {}).get("model_id") or state.get(
            "model_override"
        )
        team_id = config.get("configurable", {}).get("team_id")

        try:
            # Get the model provisioned
            model = await provision_langchain_model(
                str(payload),
                model_id,
                "chat",
                team_id=team_id,
                max_tokens=8192,
                streaming=True, # Enable streaming explicitly
            )
        except RuntimeError:
            # Fallback to run if not in a running loop
            model = asyncio.run(
                provision_langchain_model(
                    str(payload),
                    model_id,
                    "chat",
                    team_id=team_id,
                    max_tokens=8192,
                    streaming=True, # Enable streaming explicitly
                )
            )

        if state.get("enable_web_search"):
            from open_notebook.graphs.tools import tavily_search
            model = model.bind_tools([tavily_search])

        ai_message = await model.ainvoke(payload, config=config)

        # Clean thinking content from AI response (e.g., <think>...</think> tags)
        content = extract_text_content(ai_message.content)
        cleaned_content = clean_thinking_content(content)
        cleaned_message = ai_message.model_copy(update={"content": cleaned_content})

        return {"messages": cleaned_message}
    except OpenNotebookError:
        raise
    except Exception as e:
        import traceback

        from loguru import logger
        logger.error(f"Error in chat streaming: {str(e)}\n{traceback.format_exc()}")
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

from open_notebook.graphs.tools import tavily_search

# Create ToolNode
tool_node = ToolNode([tavily_search])

agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("tools", tool_node)

agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges("agent", tools_condition)
agent_state.add_edge("tools", "agent")
# Module-level: use MemorySaver (not SqliteSaver) to avoid concurrent sqlite write conflicts.
# The router (api/routers/chat.py) uses its own AsyncSqliteSaver with a separate file.
memory = MemorySaver()
graph = agent_state.compile(checkpointer=memory)
