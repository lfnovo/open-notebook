import streamlit as st

from open_notebook.graphs.chat import ThreadState, graph
from open_notebook.utils import (
    compare_versions,
    get_installed_version,
    get_version_from_github,
)


def version_sidebar():
    with st.sidebar:
        try:
            current_version = get_installed_version(
                "open-notebook"
            )  # Note the hyphen instead of underscore
        except Exception:
            # Fallback to reading directly from pyproject.toml
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                current_version = pyproject["tool"]["poetry"]["version"]

        latest_version = get_version_from_github(
            "https://www.github.com/lfnovo/open-notebook", "main"
        )
        st.write(f"Open Notebook: {current_version}")
        if compare_versions(current_version, latest_version) < 0:
            st.warning(
                f"New version {latest_version} available. [Click here for upgrade instructions](https://github.com/lfnovo/open-notebook/blob/main/docs/SETUP.md#upgrading-open-notebook)"
            )


def setup_stream_state(session_id) -> None:
    """
    Sets the value of the current session_id for langgraph thread state.
    If there is no existing thread state for this session_id, it creates a new one.
    """
    existing_state = graph.get_state({"configurable": {"thread_id": session_id}}).values
    if len(existing_state.keys()) == 0:
        st.session_state[session_id] = ThreadState(
            messages=[], context=None, notebook=None, context_config={}, response=None
        )
    else:
        st.session_state[session_id] = existing_state
    st.session_state["active_session"] = session_id
    st.session_state["active_session"] = session_id
