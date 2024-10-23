from pathlib import Path

import streamlit as st
import streamlit_scrollable_textbox as stx  # type: ignore
import yaml
from humanize import naturaltime
from loguru import logger

from open_notebook.domain import Asset, Source
from open_notebook.graphs.content_process import graph
from open_notebook.graphs.multipattern import graph as transform_graph
from open_notebook.utils import surreal_clean

from .consts import context_icons

uploads_dir = Path("./.uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)


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
                    if st.button("Delete", key=f"delete_insight_{insight.id}"):
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

            if st.button("Delete", icon="🗑️"):
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
        if source_file is not None:
            # Get the file name and extension
            file_name = source_file.name

            file_extension = Path(file_name).suffix

            # Generate a unique file name
            base_name = Path(file_name).stem
            counter = 1
            new_path = uploads_dir / file_name
            while new_path.exists():
                new_file_name = f"{base_name}_{counter}{file_extension}"
                new_path = uploads_dir / new_file_name
                counter += 1

            req["file_path"] = str(new_path)
            # Save the file
            with open(new_path, "wb") as f:
                f.write(source_file.getbuffer())

    else:
        source_text = st.text_area("Text")
        req["content"] = source_text
    if st.button("Process", key="add_source"):
        logger.debug("Adding source")
        with st.status("Processing...", expanded=True):
            st.write("Processing document...")
            result = graph.invoke(req)
            st.write("Saving..")
            source = Source(
                asset=Asset(url=req.get("url"), file_path=req.get("file_path")),
                full_text=surreal_clean(result["content"]),
            )
            source.save()
            source.add_to_notebook(st.session_state[session_id]["notebook"].id)
            st.write("Summarizing...")
            source.summarize()

        st.rerun()


def source_card(session_id, source):
    icon = "🔗"
    context_state = st.selectbox(
        "Context",
        label_visibility="collapsed",
        options=context_icons,
        index=0,
        key=f"source_{source.id}",
    )
    with st.expander(f"**{source.title}**"):
        st.markdown(f"{icon} Updated: {naturaltime(source.updated)}")
        st.markdown("**" + ", ".join(source.topics) + "**")
        for insight in source.insights:
            st.write(insight.insight_type)
            st.write(insight.content)

        if st.button("Edit Source", icon="📝", key=source.id):
            source_panel(source.id)

        # with st.popover("Actions"):
        #     if st.button("Edit Source", icon="📝", key=source.id):
        #         result = source_panel(source.id)
        #         st.write(result)
        #     if st.button("Delete", icon="🗑️", key=f"delete_options_{source.id}"):
        #         source.delete()
        #         st.rerun()

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
