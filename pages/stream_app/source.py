import os
from pathlib import Path

import streamlit as st
from humanize import naturaltime
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Asset, Source
from open_notebook.exceptions import UnsupportedTypeException
from open_notebook.graphs.content_processing import graph
from open_notebook.utils import surreal_clean
from pages.components import source_panel
from pages.stream_app.utils import run_patterns

from .consts import context_icons


# moved it here to replace it with the pipeline on 0.1.0
def generate_toc_and_title(source) -> "Source":
    try:
        patterns = ["patterns/default/toc"]
        result = run_patterns(source.full_text, patterns=patterns)
        source.add_insight("Table of Contents", surreal_clean(result))
        if not source.title:
            patterns = [
                "Based on the Table of Contents below, please provide a Title for this content, with max 15 words"
            ]
            output = run_patterns(result, patterns=patterns)
            source.title = surreal_clean(output)
            source.save()
        return source
    except Exception as e:
        logger.error(f"Error summarizing source {source.id}: {str(e)}")
        logger.exception(e)
        raise


@st.dialog("Source", width="large")
def source_panel_dialog(source_id):
    source_panel(source_id)


@st.dialog("Add a Source", width="large")
def add_source(notebook_id):
    source_link = None
    source_file = None
    source_text = None
    source_type = st.radio("Type", ["Link", "Upload", "Text"])
    req = {}
    if source_type == "Link":
        source_link = st.text_input("Link")
        req["url"] = source_link
    elif source_type == "Upload":
        source_file = st.file_uploader("Upload")
        req["delete_source"] = st.checkbox("Delete source after processing", value=True)

    else:
        source_text = st.text_area("Text")
        req["content"] = source_text
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

                result = graph.invoke(req)
                st.write("Saving..")
                source = Source(
                    asset=Asset(url=req.get("url"), file_path=req.get("file_path")),
                    full_text=surreal_clean(result["content"]),
                    title=result.get("title"),
                )
                source.save()
                source.add_to_notebook(notebook_id)
                st.write("Summarizing...")
                generate_toc_and_title(source)
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
            options=context_icons,
            index=0,
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
