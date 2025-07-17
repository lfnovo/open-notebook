import streamlit as st
from loguru import logger
from streamlit_monaco import st_monaco  # type: ignore

from api.models_service import ModelsService
from api.notes_service import NotesService
from pages.stream_app.utils import convert_source_references

# Initialize service instances
models_service = ModelsService()
notes_service = NotesService()


def note_panel(note_id, notebook_id=None):
    default_models = models_service.get_default_models()
    if not default_models.default_embedding_model:
        st.warning(
            "Since there is no embedding model selected, your note will be saved but not searchable."
        )
    note = notes_service.get_note(note_id)
    if not note:
        raise ValueError(f"Note not fonud {note_id}")
    t_preview, t_edit = st.tabs(["Preview", "Edit"])
    with t_preview:
        st.subheader(note.title)
        st.markdown(convert_source_references(note.content))
    with t_edit:
        note.title = st.text_input("Title", value=note.title)
        note.content = st_monaco(
            value=note.content, height="300px", language="markdown"
        )
        b1, b2 = st.columns(2)
        if b1.button("Save", key=f"pn_edit_note_{note.id or 'new'}"):
            logger.debug("Editing note")
            if note.id:
                notes_service.update_note(note)
            else:
                note = notes_service.create_note(
                    content=note.content,
                    title=note.title,
                    note_type=note.note_type,
                    notebook_id=notebook_id,
                )
            st.rerun()
    if b2.button("Delete", type="primary", key=f"delete_note_{note.id or 'new'}"):
        logger.debug("Deleting note")
        if note.id:
            notes_service.delete_note(note.id)
        st.rerun()
