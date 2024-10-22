from pathlib import Path

import streamlit as st
import streamlit_scrollable_textbox as stx  # type: ignore
from humanize import naturaltime
from loguru import logger
from streamlit_tags import st_tags  # type: ignore

from open_notebook.domain import Asset, Source
from open_notebook.graphs.content_process import graph
from open_notebook.utils import token_cost, token_count

from .consts import context_icons

uploads_dir = Path("./.uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)


@st.dialog("Source", width="large")
def source_panel(source_id):
    source: Source = Source.get(source_id)
    if not source:
        st.error("Source not found")
        return
    title = st.empty()
    if source.title:
        title.subheader(source.title)
    st.caption(f"Created {naturaltime(source.created)}")
    # st.markdown(f"**URL:** {source.url}, **File:** {source.file_path}")
    summary = st.empty()
    for insight in source.insights:
        summary.write(insight.insight_type)
        summary.write(insight.content)

    topics = source.topics or []
    if len(topics) > 0:
        st_tags(
            label="",
            text="Press enter to add more",
            value=source.topics,
            suggestions=source.topics,
            maxtags=10,
            key="1",
        )

    if st.button("Delete", icon="🗑️"):
        source.delete()
        st.rerun()

    cost = token_cost(token_count(source.full_text)) * 1.2
    if st.button(f"Summarize (about ${cost:.4f})", icon="📝"):
        source.summarize()
        st.rerun(scope="fragment")

    cost_embedding = token_cost(token_count(source.full_text), 0.02)

    if st.button(f"Embed (${cost_embedding:.4f})", icon="📝"):
        source.vectorize()
        st.success("Embedding complete")

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
            )
            source.save()
            source.save_chunks(result["content"])
            source.add_to_notebook(st.session_state[session_id]["notebook"].id)
            st.write("Summarizing...")
            source.summarize()

        st.rerun()
    # else:
    #     st.stop()


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
