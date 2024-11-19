from typing import Optional

import streamlit as st
from humanize import naturaltime

from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import Note
from open_notebook.graphs.prompt import graph as prompt_graph
from open_notebook.utils import surreal_clean
from pages.components import note_panel

from .consts import note_context_icons


@st.dialog("Write a Note", width="large")
def add_note(notebook_id):
    if not model_manager.embedding_model:
        st.warning(
            "Since there is no embedding model selected, your note will be saved but not searchable."
        )
    note_title = st.text_input("Title")
    note_content = st.text_area("Content")
    if st.button("Save", key="add_note"):
        note = Note(title=note_title, content=note_content, note_type="human")
        note.save()
        note.add_to_notebook(notebook_id)
        st.rerun()


@st.dialog("Add a Note", width="large")
def note_panel_dialog(note: Optional[Note] = None, notebook_id=None):
    note_panel(note_id=note.id, notebook_id=notebook_id)


def make_note_from_chat(content, notebook_id=None):
    # todo: make this more efficient
    prompt = "Based on the Note below, please provide a Title for this content, with max 15 words"
    output = prompt_graph.invoke(dict(input_text=content, prompt=prompt))
    title = surreal_clean(output["output"])

    note = Note(
        title=title,
        content=content,
        note_type="ai",
    )
    note.save()
    if notebook_id:
        note.add_to_notebook(notebook_id)

    st.rerun()


def note_card(note, notebook_id):
    if note.note_type == "human":
        icon = "🤵"
    else:
        icon = "🤖"

    with st.container(border=True):
        st.markdown((f"{icon} **{note.title if note.title else 'No Title'}**"))
        context_state = st.selectbox(
            "Context",
            label_visibility="collapsed",
            options=note_context_icons,
            index=1,
            key=f"note_{note.id}",
        )
        st.caption(f"Updated: {naturaltime(note.updated)}")

        if st.button("Expand", icon="📝", key=f"edit_note_{note.id}"):
            note_panel_dialog(notebook_id=notebook_id, note=note)

    st.session_state[notebook_id]["context_config"][note.id] = context_state


def note_list_item(note_id, score=None):
    note: Note = Note.get(note_id)
    if note.note_type == "human":
        icon = "🤵"
    else:
        icon = "🤖"

    with st.expander(
        f"{icon} [{score:.2f}] **{note.title}** {naturaltime(note.updated)}"
    ):
        st.write(note.content)
        if st.button("Edit Note", icon="📝", key=f"x_edit_note_{note.id}"):
            note_panel_dialog(note=note)
