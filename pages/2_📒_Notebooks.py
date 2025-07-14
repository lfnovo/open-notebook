import streamlit as st
from humanize import naturaltime

from api.notebook_service import notebook_service
from api.notes_service import notes_service
from api.sources_service import sources_service
from open_notebook.domain.notebook import Notebook
from pages.stream_app.chat import chat_sidebar
from pages.stream_app.note import add_note, note_card
from pages.stream_app.source import add_source, source_card
from pages.stream_app.utils import setup_page, setup_stream_state

setup_page("📒 Open Notebook", only_check_mandatory_models=True)


def notebook_header(current_notebook: Notebook):
    """
    Defines the header of the notebook page, including the ability to edit the notebook's name and description.
    """
    c1, c2, c3 = st.columns([8, 2, 2])
    c1.header(current_notebook.name)
    if c2.button("Back to the list", icon="🔙"):
        st.session_state["current_notebook_id"] = None
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
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("Save", icon="💾", key="edit_notebook"):
            current_notebook.name = notebook_name
            current_notebook.description = notebook_description
            notebook_service.update_notebook(current_notebook)
            st.rerun()
        if not current_notebook.archived:
            if c2.button("Archive", icon="🗃️"):
                current_notebook.archived = True
                notebook_service.update_notebook(current_notebook)
                st.toast("Notebook archived", icon="🗃️")
        else:
            if c2.button("Unarchive", icon="🗃️"):
                current_notebook.archived = False
                notebook_service.update_notebook(current_notebook)
                st.toast("Notebook unarchived", icon="🗃️")
        if c3.button("Delete forever", type="primary", icon="☠️"):
            notebook_service.delete_notebook(current_notebook)
            st.session_state["current_notebook_id"] = None
            st.rerun()


def notebook_page(current_notebook: Notebook):
    # Guarantees that we have an entry for this notebook in the session state
    if current_notebook.id not in st.session_state:
        st.session_state[current_notebook.id] = {"notebook": current_notebook}

    # sets up the active session
    current_session = setup_stream_state(
        current_notebook=current_notebook,
    )

    sources = sources_service.get_all_sources(notebook_id=current_notebook.id)
    notes = notes_service.get_all_notes(notebook_id=current_notebook.id)

    notebook_header(current_notebook)

    work_tab, chat_tab = st.columns([4, 2])
    with work_tab:
        sources_tab, notes_tab = st.columns(2)
        with sources_tab:
            with st.container(border=True):
                if st.button("Add Source", icon="➕"):
                    add_source(current_notebook.id)
                for source in sources:
                    source_card(source=source, notebook_id=current_notebook.id)

        with notes_tab:
            with st.container(border=True):
                if st.button("Write a Note", icon="📝"):
                    add_note(current_notebook.id)
                for note in notes:
                    note_card(note=note, notebook_id=current_notebook.id)
    with chat_tab:
        chat_sidebar(current_notebook=current_notebook, current_session=current_session)


def notebook_list_item(notebook):
    with st.container(border=True):
        st.subheader(notebook.name)
        st.caption(
            f"Created: {naturaltime(notebook.created)}, updated: {naturaltime(notebook.updated)}"
        )
        st.write(notebook.description)
        if st.button("Open", key=f"open_notebook_{notebook.id}"):
            st.session_state["current_notebook_id"] = notebook.id
            st.rerun()


if "current_notebook_id" not in st.session_state:
    st.session_state["current_notebook_id"] = None

# todo: get the notebook, check if it exists and if it's archived
if st.session_state["current_notebook_id"]:
    current_notebook: Notebook = notebook_service.get_notebook(st.session_state["current_notebook_id"])
    if not current_notebook:
        st.error("Notebook not found")
        st.stop()
    notebook_page(current_notebook)
    st.stop()

st.title("📒 My Notebooks")
st.caption(
    "Notebooks are a great way to organize your thoughts, ideas, and sources. You can create notebooks for different research topics and projects, to create new articles, etc. "
)

with st.expander("➕ **New Notebook**"):
    new_notebook_title = st.text_input("New Notebook Name")
    new_notebook_description = st.text_area(
        "Description",
        placeholder="Explain the purpose of this notebook. The more details the better.",
    )
    if st.button("Create a new Notebook", icon="➕"):
        notebook = notebook_service.create_notebook(
            name=new_notebook_title, description=new_notebook_description
        )
        st.toast("Notebook created successfully", icon="📒")

notebooks = notebook_service.get_all_notebooks(order_by="updated desc")
archived_notebooks = [nb for nb in notebooks if nb.archived]

for notebook in notebooks:
    if notebook.archived:
        continue
    notebook_list_item(notebook)

if len(archived_notebooks) > 0:
    with st.expander(f"**🗃️ {len(archived_notebooks)} archived Notebooks**"):
        st.write("ℹ Archived Notebooks can still be accessed and used in search.")
        for notebook in archived_notebooks:
            notebook_list_item(notebook)
