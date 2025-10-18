import asyncio
import re
from datetime import datetime
from typing import Optional

import nest_asyncio
import streamlit as st
from loguru import logger

nest_asyncio.apply()
from api.chat_service import chat_service
from api.models_service import models_service
from open_notebook.utils import (
    compare_versions,
    get_installed_version,
    get_version_from_github,
)


def version_sidebar():
    with st.sidebar:
        # Get current version
        try:
            current_version = get_installed_version("open-notebook")
        except Exception:
            # Fallback to reading directly from pyproject.toml
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                current_version = pyproject["project"]["version"]

        st.write(f"Open Notebook: {current_version}")

        # Try to get latest version, but don't fail if unavailable
        try:
            # Use session state cache to avoid repeated checks
            if 'latest_version' not in st.session_state or 'version_check_failed' not in st.session_state:
                latest_version = get_version_from_github(
                    "https://www.github.com/lfnovo/open-notebook", "main"
                )
                st.session_state.latest_version = latest_version
                st.session_state.version_check_failed = False
            else:
                latest_version = st.session_state.latest_version

            if not st.session_state.version_check_failed and compare_versions(current_version, latest_version) < 0:
                st.warning(
                    f"New version {latest_version} available. [Click here for upgrade instructions](https://github.com/lfnovo/open-notebook/blob/main/docs/SETUP.md#upgrading-open-notebook)"
                )
        except Exception:
            # Cache the fact that version check failed to avoid repeated attempts
            st.session_state.version_check_failed = True
            # Optionally show a subtle message about failed update check
            st.caption("⚠️ Could not check for updates (offline or GitHub unavailable)")


def create_session_for_notebook(notebook_id: str, session_name: Optional[str] = None):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"Chat Session {current_time}" if not session_name else session_name
    session_data = asyncio.run(chat_service.create_session(notebook_id, title))
    return session_data


def setup_stream_state(current_notebook) -> dict:
    """
    Sets the value of the current session_id for API-based chat functionality.
    Creates or retrieves a chat session and sets up session state.
    """
    assert current_notebook is not None and current_notebook.id, (
        "Current Notebook not selected properly"
    )

    if "context_config" not in st.session_state[current_notebook.id]:
        st.session_state[current_notebook.id]["context_config"] = {}

    current_session_id = st.session_state[current_notebook.id].get("active_session")

    # gets the chat session if provided
    chat_session = None
    if current_session_id:
        try:
            chat_session = asyncio.run(chat_service.get_session(current_session_id))
        except Exception as e:
            logger.warning(f"Could not retrieve session {current_session_id}: {e}")

    # if there is no chat session, create one or get the first one
    if not chat_session:
        sessions = asyncio.run(chat_service.get_sessions(current_notebook.id))
        if not sessions or len(sessions) == 0:
            logger.debug("Creating new chat session")
            chat_session = create_session_for_notebook(current_notebook.id)
        else:
            logger.debug("Getting last updated session")
            chat_session = sessions[0]

    if not chat_session or not chat_session.get("id"):
        raise ValueError("Problem acquiring chat session")
    
    # sets the active session for the notebook
    session_id = chat_session["id"]
    st.session_state[current_notebook.id]["active_session"] = session_id

    # Initialize session state for messages if not exists
    if session_id not in st.session_state:
        # Load the full session with messages from API
        try:
            full_session = asyncio.run(chat_service.get_session(session_id))
            messages = full_session.get("messages", [])
        except Exception as e:
            logger.warning(f"Could not load messages for session {session_id}: {e}")
            messages = []
            
        st.session_state[session_id] = {
            "messages": messages,
            "context": None,
            "notebook": None,
            "context_config": {}
        }

    return chat_session


def check_migration():
    """
    DEPRECATED: This function is no longer used.
    Database migrations now run automatically when the API starts up.
    See api/main.py lifespan handler for the new migration logic.

    This function is kept for backward compatibility but does nothing.
    """
    # Migrations are now handled automatically by the API on startup
    # No user interaction needed
    if "migration_required" not in st.session_state:
        st.session_state["migration_required"] = False
    pass


def check_models(only_mandatory=True, stop_on_error=True):
    default_models = models_service.get_default_models()
    mandatory_models = [
        default_models.default_chat_model,
        default_models.default_transformation_model,
        default_models.default_embedding_model,
    ]
    all_models = mandatory_models + [
        default_models.default_speech_to_text_model,
        default_models.large_context_model,
    ]

    if not all(mandatory_models):
        st.error(
            "You are missing some default models and the app will not work as expected. Please, select them on the Models page."
        )
        if stop_on_error:
            st.stop()

    if not only_mandatory:
        if not all(all_models):
            st.warning(
                "You are missing some important optional models. The app might not work as expected. Please, select them on the Models page."
            )


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


def setup_page(
    title: str,
    layout="wide",
    sidebar_state="expanded",
    only_check_mandatory_models=True,
    stop_on_model_error=True,
    skip_model_check=False,
):
    """Common page setup for all pages"""
    st.set_page_config(
        page_title=title, layout=layout, initial_sidebar_state=sidebar_state
    )
    
    # Check authentication first
    from pages.stream_app.auth import check_password
    check_password()
    
    check_migration()
    
    # Skip model check if requested (e.g., on Models page)
    if not skip_model_check:
        check_models(
            only_mandatory=only_check_mandatory_models, stop_on_error=stop_on_model_error
        )
    
    version_sidebar()


def convert_source_references(text):
    """
    Converts source references in brackets to markdown-style links.

    Matches patterns like [source_insight:id], [note:id], [source:id], or [source_embedding:id]
    and converts them to markdown links.

    Args:
        text (str): The input text containing source references

    Returns:
        str: Text with source references converted to markdown links

    Example:
        >>> text = "Here is a reference [source_insight:abc123]"
        >>> convert_source_references(text)
        'Here is a reference [source_insight:abc123](/?object_id=source_insight:abc123)'
    """

    # Pattern matches [type:id] where type can be source_insight, note, source, or source_embedding
    pattern = r"\[((?:source_insight|note|source|source_embedding):[\w\d]+)\]"

    def replace_match(match):
        """Helper function to create the markdown link"""
        source_ref = match.group(1)  # Gets the content inside brackets
        return f"[[{source_ref}]](/?object_id={source_ref})"

    # Replace all matches in the text
    converted_text = re.sub(pattern, replace_match, text)

    return converted_text
