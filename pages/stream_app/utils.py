from datetime import datetime
from typing import List, Union

import streamlit as st
from loguru import logger

from open_notebook.database.migrate import MigrationManager
from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.graphs.chat import ThreadState, graph
from open_notebook.utils import (
    compare_versions,
    get_installed_version,
    get_version_from_github,
)


def version_sidebar():
    with st.sidebar:
        try:
            current_version = get_installed_version("open-notebook")
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


def create_session_for_notebook(notebook_id: str, session_name: str = None):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"Chat Session {current_time}" if not session_name else session_name
    chat_session = ChatSession(title=title)
    chat_session.save()
    chat_session.relate_to_notebook(notebook_id)
    return chat_session


def setup_stream_state(current_notebook: Notebook) -> ChatSession:
    """
    Sets the value of the current session_id for langgraph thread state.
    If there is no existing thread state for this session_id, it creates a new one.
    Finally, it acquires the existing state for the session from Langgraph state and sets it in the streamlit session state.
    """
    assert (
        current_notebook is not None and current_notebook.id
    ), "Current Notebook not selected properly"

    if "context_config" not in st.session_state[current_notebook.id]:
        st.session_state[current_notebook.id]["context_config"] = {}

    current_session_id = st.session_state[current_notebook.id].get("active_session")

    # gets the chat session if provided
    chat_session: Union[ChatSession, None] = (
        ChatSession.get(current_session_id) if current_session_id else None
    )

    # if there is no chat session, create one or get the first one
    if not chat_session:
        sessions: List[ChatSession] = current_notebook.chat_sessions
        if not sessions or len(sessions) == 0:
            logger.debug("Creating new chat session")
            chat_session = create_session_for_notebook(current_notebook.id)
        else:
            logger.debug("Getting last updated session")
            chat_session = sessions[0]

    logger.debug(f"Chat session: {chat_session}")

    if not chat_session or chat_session.id is None:
        raise ValueError("Problem acquiring chat session")
    # sets the active session for the notebook
    st.session_state[current_notebook.id]["active_session"] = chat_session.id

    # gets the existing state for the session from Langgraph state
    existing_state = graph.get_state(
        {"configurable": {"thread_id": chat_session.id}}
    ).values
    if not existing_state or len(existing_state.keys()) == 0:
        st.session_state[chat_session.id] = ThreadState(
            messages=[], context=None, notebook=None, context_config={}
        )
    else:
        st.session_state[chat_session.id] = existing_state

    st.session_state[current_notebook.id]["active_session"] = chat_session.id
    return chat_session


def check_migration():
    mm = MigrationManager()
    if mm.needs_migration:
        st.warning("The Open Notebook database needs a migration to run properly.")
        if st.button("Run Migration"):
            mm.run_migration_up()
            st.success("Migration successful")
            st.rerun()
        st.stop()


def check_models():
    default_models = model_manager.defaults
    if (
        not default_models.default_chat_model
        or not default_models.default_transformation_model
    ):
        st.warning(
            "You don't have default chat and transformation models selected. Please, select them on the settings page."
        )
        st.stop()
    elif not default_models.default_embedding_model:
        st.warning(
            "You don't have a default embedding model selected. Vector search will not be possible and your assistant will be less able to answer your queries. Please, select one on the settings page."
        )
        st.stop()
    elif not default_models.default_speech_to_text_model:
        st.warning(
            "You don't have a default speech to text model selected. Your assistant will not be able to transcribe audio. Please, select one on the settings page."
        )
        st.stop()
    elif not default_models.default_text_to_speech_model:
        st.warning(
            "You don't have a default text to speech model selected. Your assistant will not be able to generate audio and podcasts. Please, select one on the settings page."
        )
        st.stop()
    elif not default_models.large_context_model:
        st.warning(
            "You don't have a large context model selected. Your assistant will not be able to process large documents. Please, select one on the settings page."
        )
        st.stop()


def handle_error(func):
    """Decorator for consistent error handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.exception(e)
            st.error(f"An error occurred: {str(e)}")

    return wrapper


def setup_page(title: str, layout="wide", sidebar_state="expanded"):
    """Common page setup for all pages"""
    st.set_page_config(
        page_title=title, layout=layout, initial_sidebar_state=sidebar_state
    )
    check_migration()
    check_models()
    version_sidebar()
