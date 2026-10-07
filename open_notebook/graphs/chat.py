import asyncio
import sqlite3
from typing import Annotated, Optional

from ai_prompter import Prompter
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.config import LANGGRAPH_CHECKPOINT_FILE
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import IncompleteGenerationError, OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.chat_images import chat_model_context
from open_notebook.utils.chat_responses import (
    latest_request,
    quiz_instructions,
    requested_widgets,
    run_chat_response,
)
from open_notebook.utils.chat_visuals import run_visual_chat
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content


class ThreadState(TypedDict):
    messages: Annotated[list, add_messages]
    notebook: Optional[Notebook]
    context: Optional[str]
    context_config: Optional[dict]
    visual_tools: NotRequired[bool]
    model_override: Optional[str]


def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        system_prompt = Prompter(prompt_template="chat/system").render(data=state)  # type: ignore[arg-type]
        payload = [
            SystemMessage(content=system_prompt + quiz_instructions())
        ] + state.get("messages", [])
        model_id = config.get("configurable", {}).get("model_id") or state.get(
            "model_override"
        )

        # Handle async model provisioning from sync context
        def run_in_new_loop():
            """Run the async function in a new event loop"""
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(
                    provision_langchain_model(
                        chat_model_context(payload), model_id, "chat", max_tokens=8192
                    )
                )
            finally:
                new_loop.close()
                asyncio.set_event_loop(None)

        try:
            # Try to get the current event loop
            asyncio.get_running_loop()
            # If we're in an event loop, run in a thread with a new loop
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_new_loop)
                model = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            model = asyncio.run(
                provision_langchain_model(
                    chat_model_context(payload),
                    model_id,
                    "chat",
                    max_tokens=8192,
                )
            )

        if state.get("visual_tools") or requested_widgets(latest_request(payload))[0]:

            async def available_sources():
                notebook = state.get("notebook")
                sources = await notebook.get_sources() if notebook else []
                context = state.get("context")
                selected: set[str] = (
                    {
                        str(item.get("id"))
                        for item in context.get("sources", [])
                        if isinstance(item, dict)
                    }
                    if isinstance(context, dict)
                    else set()
                )
                return {str(source.id) for source in sources} & selected

            def get_ids():
                return asyncio.run(available_sources())

            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                source_ids = executor.submit(get_ids).result()
            ai_message = run_visual_chat(model, payload, source_ids, model_id)
        else:
            ai_message = model.invoke(payload)

        # Clean thinking content from AI response (e.g., <think>...</think> tags)
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

        cleaned_message = run_chat_response(
            cleaned_message,
            config.get("configurable", {}).get("thread_id", ""),
            config.get("configurable", {}).get("model_id")
            or state.get("model_override"),
            latest_request(payload),
            extract_text_content(payload[0].content),
        )

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
memory = SqliteSaver(conn)

agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile(checkpointer=memory)
