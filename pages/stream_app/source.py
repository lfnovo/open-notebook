import asyncio
import os
from pathlib import Path

import streamlit as st
from humanize import naturaltime
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultTransformations, Transformation
from open_notebook.exceptions import UnsupportedTypeException
from open_notebook.graphs.source import source_graph
from pages.components import source_panel

from .consts import source_context_icons


@st.dialog("Source", width="large")
def source_panel_dialog(source_id):
    source_panel(source_id, modal=True)


@st.dialog("Add a Source", width="large")
def add_source(notebook_id):
    source_link = None
    source_file = None
    source_text = None
    source_type = st.radio("Type", ["Link", "Upload", "Text"])
    req = {}
    transformations = Transformation.get_all()
    if source_type == "Link":
        source_link = st.text_input("Link")
        req["url"] = source_link
    elif source_type == "Upload":
        source_file = st.file_uploader("Upload")
        req["delete_source"] = st.checkbox("Delete source after processing", value=True)

    else:
        source_text = st.text_area("Text")
        req["content"] = source_text

    default_transformations = [t for t in DefaultTransformations().source_insights]
    available_transformations = [t["name"] for t in transformations["source_insights"]]
    apply_transformations = st.multiselect(
        "Apply transformations",
        options=available_transformations,
        default=default_transformations,
    )
    run_embed = st.checkbox(
        "Embed content for vector search",
        help="Creates an embedded content for vector search. Costs a little money and takes a little bit more time. You can do this later if you prefer.",
    )
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
                            "transformations": apply_transformations,
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
            source_panel_dialog(source.id)

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
