import os
from pathlib import Path

import streamlit as st
import streamlit_scrollable_textbox as stx  # type: ignore
import yaml
from humanize import naturaltime
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Asset, Source
from open_notebook.exceptions import UnsupportedTypeException
from open_notebook.graphs.content_processing import graph
from open_notebook.graphs.multipattern import graph as transform_graph
from open_notebook.utils import surreal_clean

from .consts import context_icons


def run_transformations(input_text, transformations):
    output = transform_graph.invoke(
        dict(content_stack=[input_text], transformations=transformations)
    )
    return output["output"]


@st.dialog("Source", width="large")
def source_panel(source_id):
    source: Source = Source.get(source_id)
    if not source:
        st.error("Source not found")
        return
    current_title = source.title if source.title else "No Title"
    source.title = st.text_input("Title", value=current_title)
    if source.title != current_title:
        st.toast("Saved new Title")
        source.save()

    process_tab, source_tab = st.tabs(["Process", "Source"])
    with process_tab:
        c1, c2 = st.columns([3, 1])
        with c1:
            title = st.empty()
            if source.title:
                title.subheader(source.title)
            if source.asset.url:
                from_src = f"from URL: {source.asset.url}"
            elif source.asset.file_path:
                from_src = f"from file: {source.asset.file_path}"
            else:
                from_src = "from text"
            st.caption(f"Created {naturaltime(source.created)}, {from_src}")
            for insight in source.insights:
                with st.expander(f"**{insight.insight_type}**"):
                    st.markdown(insight.content)
                    if st.button(
                        "Delete", type="primary", key=f"delete_insight_{insight.id}"
                    ):
                        insight.delete()
                        st.rerun(scope="fragment")

        with c2:
            with open("transformations.yaml", "r") as file:
                transformations = yaml.safe_load(file)
                for transformation in transformations["source_insights"]:
                    if st.button(
                        transformation["name"], help=transformation["description"]
                    ):
                        result = run_transformations(
                            source.full_text, transformation["transformations"]
                        )
                        source.add_insight(
                            transformation["insight_type"], surreal_clean(result)
                        )
                        st.rerun(scope="fragment")

            if st.button(
                "Embed vectors",
                icon="🦾",
                help="This will generate your embedding vectors on the database for powerful search capabilities",
            ):
                source.vectorize()
                st.success("Embedding complete")

            chk_delete = st.checkbox(
                "🗑️ Delete source", key=f"delete_source_{source.id}", value=False
            )
            if chk_delete:
                st.warning(
                    "Source will be deleted with all its insights and embeddings"
                )
                if st.button(
                    "Delete", type="primary", key=f"bt_delete_source_{source.id}"
                ):
                    source.delete()
                    st.rerun()

    with source_tab:
        st.subheader("Content")
        stx.scrollableTextbox(source.full_text, height=300)


@st.dialog("Add a Source", width="large")
def add_source(session_id):
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
                source.add_to_notebook(st.session_state[session_id]["notebook"].id)
                st.write("Summarizing...")
                source.generate_toc_and_title()
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
                st.error(e)
                return

        st.rerun()


def source_card(session_id, source):
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
            source_panel(source.id)

    st.session_state[session_id]["context_config"][source.id] = context_state


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
            source_panel(source_id=source.id)
