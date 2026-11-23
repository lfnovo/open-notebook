import sqlite3
from typing import Annotated, Optional

from ai_prompter import Prompter
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.config import LANGGRAPH_CHECKPOINT_FILE
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import IncompleteGenerationError, OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.checkpointing import HybridSqliteSaver
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content


class ThreadState(TypedDict):
    messages: Annotated[list, add_messages]
    notebook: Optional[Notebook]
    context: Optional[str]
    context_config: Optional[dict]
    model_override: Optional[str]


# The graph's only node. Streaming attributes its checkpoint writes to it
# (`persist_state(..., as_node=NODE_NAME)`) and filters token chunks by it.
NODE_NAME = "agent"


def build_chat_payload(state: ThreadState) -> list:
    """Render the system prompt and prepend it to the thread's messages."""
    system_prompt = Prompter(prompt_template="chat/system").render(data=state)  # type: ignore[arg-type]
    return [SystemMessage(content=system_prompt)] + state.get("messages", [])


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    """Answer the thread's last message.

    Async so `graph.astream(..., stream_mode="messages")` can forward tokens
    while the node runs, and so a cancelled stream closes the provider request
    instead of letting it run to completion.
    """
    try:
        payload = build_chat_payload(state)
        model_id = config.get("configurable", {}).get("model_id") or state.get(
            "model_override"
        )

        # `streaming=True` is required for astream() to forward deltas rather
        # than fall back to a single whole-message chunk.
        model = await provision_langchain_model(
            str(payload), model_id, "chat", max_tokens=8192, streaming=True
        )

        ai_message = await model.ainvoke(payload)

        # Clean thinking content from AI response (e.g.,  thinking...</think> tags)
        content = extract_text_content(ai_message.content)
        cleaned_content = clean_thinking_content(content)
        if not cleaned_content.strip():
            # Raising inside the node keeps LangGraph from checkpointing a
            # blank AI message that would be replayed as context later.
            raise IncompleteGenerationError(
                "The model returned an empty response. Try again, or pick a "
                "different model if this keeps happening."
            )
        cleaned_message = ai_message.model_copy(update={"content": cleaned_content})

        return {"messages": cleaned_message}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


conn = sqlite3.connect(
    LANGGRAPH_CHECKPOINT_FILE,
    check_same_thread=False,
)
memory = HybridSqliteSaver(conn)

agent_state = StateGraph(ThreadState)
agent_state.add_node(NODE_NAME, call_model_with_messages)
agent_state.add_edge(START, NODE_NAME)
agent_state.add_edge(NODE_NAME, END)
graph = agent_state.compile(checkpointer=memory)
