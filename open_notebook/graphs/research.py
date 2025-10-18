"""Integration layer for the deep research LangGraph within Open Notebook."""

from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableConfig

from open_deep_research.configuration import SearchAPI
from open_deep_research.deep_researcher import deep_researcher


# Compile the deep research graph without persistent checkpointing for now.
graph = deep_researcher


def build_runnable_config(
    notebook_id: str, #notebookID should not be optional!
    overrides: Optional[Dict[str, Any]] = None,
) -> RunnableConfig:
    """Prepare a runnable config that injects notebook-aware defaults."""

    configurable: Dict[str, Any] = {
        "search_api": SearchAPI.NOTEBOOK.value,
    }

    
    configurable["notebook_id"] = notebook_id

    if overrides:
        configurable.update(overrides)

    return RunnableConfig(configurable=configurable)
