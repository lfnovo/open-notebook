from langchain_core.runnables import RunnableConfig
from loguru import logger

async def get_session_message_count(graph, session_id: str) -> int:
    """Get message count from LangGraph state, returns 0 on error."""
    try:
        thread_state = await graph.aget_state( # async version
            config=RunnableConfig(configurable={"thread_id": session_id})
        )
        if (
            thread_state
            and thread_state.values
            and "messages" in thread_state.values
        ):
            return len(thread_state.values["messages"])
    except Exception as e:
        logger.warning(f"Could not fetch message count for session {session_id}: {e}")
    return 0
