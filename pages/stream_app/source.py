import asyncio
import os
from pathlib import Path

import nest_asyncio
import streamlit as st
from humanize import naturaltime
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import UnsupportedTypeException
from open_notebook.graphs.source import source_graph
from pages.components import source_panel
from pages.stream_app.consts import source_context_icons

nest_asyncio.apply()


@st.dialog("Source", width="large")
def source_panel_dialog(source_id, notebook_id=None):
    source_panel(source_id, notebook_id=notebook_id, modal=True)


@st.dialog("Add a Source", width="large")
def add_source(notebook_id):
    if not model_manager.speech_to_text:
        st.warning(
            "Since there is no speech to text model selected, you can't upload audio/video files."
        )
    source_link = None
    source_file = None
    source_text = None
    content_settings = ContentSettings()
    source_type = st.radio("Type", ["Link", "Upload", "Text"])
    req = {}
    transformations = Transformation.get_all()
    if source_type == "Link":
        source_link = st.text_input("Link")
        req["url"] = source_link
    elif source_type == "Upload":
        source_file = st.file_uploader("Upload")
        req["delete_source"] = content_settings.auto_delete_files == "yes"

    else:
        source_text = st.text_area("Text")
        req["content"] = source_text

    transformations = Transformation.get_all()
    default_transformations = [t for t in transformations if t.apply_default]
    apply_transformations = st.multiselect(
        "Apply transformations",
        options=transformations,
        format_func=lambda t: t.name,
        default=default_transformations,
    )
    if content_settings.default_embedding_option == "ask":
        run_embed = st.checkbox(
            "Embed content for vector search",
            help="Creates an embedded content for vector search. Costs a little money and takes a little bit more time. You can do this later if you prefer.",
        )
        if not run_embed:
            st.caption("You can always embed later by clicking on the source.")
    elif content_settings.default_embedding_option == "always":
        st.caption("Embedding content for vector search automatically")
        run_embed = True
    else:
        st.caption(
            "Not embedding content for vector search as per settings. You can always embed later by clicking on the source."
        )
        run_embed = False

    if st.button("Process", key="add_source"):
        logger.debug("Adding source")
        with st.status("Processing...", expanded=True):
            st.write("Processing document...")
            try:
                if source_type == "Upload" and source_file is not None:
                    st.write("Uploading..")
                    file_name = source_file.name
                    file_extension = Path(file_name).suffix
                    base_name = Path(file_name).stem

                    # Generate unique filename
                    new_path = os.path.join(UPLOADS_FOLDER, file_name)
                    counter = 0
                    while os.path.exists(new_path):
                        counter += 1
                        new_file_name = f"{base_name}_{counter}{file_extension}"
                        new_path = os.path.join(UPLOADS_FOLDER, new_file_name)

                    req["file_path"] = str(new_path)
                    # Save the file
                    with open(new_path, "wb") as f:
                        f.write(source_file.getbuffer())

                asyncio.run(
                    source_graph.ainvoke(
                        {
                            "content_state": req,
                            "notebook_id": notebook_id,
                            "apply_transformations": apply_transformations,
                            "embed": run_embed,
                        }
                    )
                )
            except UnsupportedTypeException as e:
                st.warning(
                    "This type of content is not supported yet. If you think it should be, let us know on the project Issues's page"
                )
                st.error(e)
                st.link_button(
                    "Go to Github Issues",
                    url="https://www.github.com/lfnovo/open-notebook/issues",
                )
                st.stop()

            except Exception as e:
                st.exception(e)
                return

        st.rerun()


def source_card(source, notebook_id):
    # todo: more descriptive icons
    icon = "🔗"

    with st.container(border=True):
        title = (source.title if source.title else "No Title").strip()
        st.markdown((f"{icon}**{title}**"))
        context_state = st.selectbox(
            "Context",
            label_visibility="collapsed",
            options=source_context_icons,
            index=1,
            key=f"source_{source.id}",
        )
        st.caption(
            f"Updated: {naturaltime(source.updated)}, **{len(source.insights)}** insights"
        )
        if st.button("Expand", icon="📝", key=source.id):
            source_panel_dialog(source.id, notebook_id)

    st.session_state[notebook_id]["context_config"][source.id] = context_state


def source_list_item(source_id, score=None):
    source: Source = Source.get(source_id)
    if not source:
        st.error("Source not found")
        return
    icon = "🔗"

    with st.expander(
        f"{icon} [{score:.2f}] **{source.title}** {naturaltime(source.updated)}"
    ):
        for insight in source.insights:
            st.markdown(f"**{insight.insight_type}**")
            st.write(insight.content)
        if st.button("Edit source", icon="📝", key=f"x_edit_source_{source.id}"):
            source_panel_dialog(source_id=source.id)
