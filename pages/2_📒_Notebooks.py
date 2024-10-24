import streamlit as st
from humanize import naturaltime

from open_notebook.domain import Notebook
from stream_app.chat import chat_sidebar
from stream_app.note import add_note, note_card
from stream_app.source import add_source, source_card
from stream_app.utils import setup_stream_state

st.set_page_config(
    layout="wide", page_title="📒 Open Notebook", initial_sidebar_state="expanded"
)


def notebook_header(current_notebook):
    c1, c2, c3 = st.columns([8, 2, 2])
    c1.header(current_notebook.name)
    if c2.button("Back to the list", icon="🔙"):
        st.session_state["current_notebook"] = None
        st.rerun()

    if c3.button("Refresh", icon="🔄"):
        st.rerun()
    current_description = current_notebook.description
    with st.expander(
        current_notebook.description
        if len(current_description) > 0
        else "click to add a description"
    ):
        notebook_name = st.text_input("Name", value=current_notebook.name)
        notebook_description = st.text_area(
            "Description",
            value=current_description,
            placeholder="Add as much context as you can as this will be used by the AI to generate insights.",
        )
        if st.button("Save", icon="💾", key="edit_notebook"):
            current_notebook.name = notebook_name
            current_notebook.description = notebook_description
            current_notebook.save()
            st.rerun()
        if st.button("Delete forever", type="primary", icon="☠️"):
            current_notebook.delete()
            st.session_state["current_notebook"] = None
            st.rerun()


def notebook_page(current_notebook_id):
    current_notebook: Notebook = Notebook.get(current_notebook_id)
    if not current_notebook:
        st.error("Notebook not found")
        return
    if current_notebook_id not in st.session_state.keys():
        st.session_state[current_notebook_id] = current_notebook

    session_id = st.session_state["active_session"]
    st.session_state[session_id]["notebook"] = current_notebook
    sources = current_notebook.sources
    notes = current_notebook.notes

    notebook_header(current_notebook)

    work_tab, chat_tab = st.columns([4, 2])
    with work_tab:
        sources_tab, notes_tab = st.columns(2)
        with sources_tab:
            with st.container(border=True):
                if st.button("Add Source", icon="➕"):
                    add_source(session_id)
                for source in sources:
                    source_card(session_id=session_id, source=source)

        with notes_tab:
            with st.container(border=True):
                if st.button("Write a Note", icon="📝"):
                    add_note(session_id)
                for note in notes:
                    note_card(session_id=session_id, note=note)
    with chat_tab:
        chat_sidebar(session_id=session_id)


if "current_notebook" not in st.session_state:
    st.session_state["current_notebook"] = None

if st.session_state["current_notebook"]:
    notebook_page(st.session_state["current_notebook"])
    st.stop()

st.title("📒 My Notebooks")
st.caption("Here are all your notebooks")


notebooks = Notebook.get_all()

for notebook in notebooks:
    with st.container(border=True):
        st.subheader(notebook.name)
        st.caption(
            f"Created: {naturaltime(notebook.created)}, updated: {naturaltime(notebook.updated)}"
        )
        st.write(notebook.description)
        if st.button("Open", key=f"open_notebook_{notebook.id}"):
            setup_stream_state(notebook.id)
            st.session_state["current_notebook"] = notebook.id
            st.rerun()

with st.container(border=True):
    new_notebook_title = st.text_input("New Notebook Name")
    new_notebook_description = st.text_area("Description")
    if st.button("Create a new Notebook", icon="➕"):
        notebook = Notebook(
            name=new_notebook_title, description=new_notebook_description
        )
        notebook.save()
        st.rerun()
