import streamlit as st

from open_notebook.config import DEFAULT_MODELS
from open_notebook.database.migrate import MigrationManager
from stream_app.utils import version_sidebar

version_sidebar()
mm = MigrationManager()
if mm.needs_migration:
    st.warning("The Open Notebook database needs a migration to run properly.")
    if st.button("Run Migration"):
        mm.run_migration_up()
        st.success("Migration successful")
        st.rerun()
elif (
    not DEFAULT_MODELS.default_chat_model
    or not DEFAULT_MODELS.default_transformation_model
):
    st.warning(
        "You don't have default chat and transformation models selected. Please, select them on the settings page."
    )
    st.stop()
elif not DEFAULT_MODELS.default_embedding_model:
    st.warning(
        "You don't have a default embedding model selected. Vector search will not be possible and your assistant will be less able to answer your queries. Please, select one on the settings page."
    )
    st.stop()
elif not DEFAULT_MODELS.default_speech_to_text_model:
    st.warning(
        "You don't have a default speech to text model selected. Your assistant will not be able to transcribe audio. Please, select one on the settings page."
    )
elif not DEFAULT_MODELS.default_text_to_speech_model:
    st.warning(
        "You don't have a default text to speech model selected. Your assistant will not be able to generate audio and podcasts. Please, select one on the settings page."
    )
elif not DEFAULT_MODELS.large_context_model:
    st.warning(
        "You don't have a large context model selected. Your assistant will not be able to process large documents. Please, select one on the settings page."
    )
else:
    st.switch_page("pages/2_📒_Notebooks.py")
