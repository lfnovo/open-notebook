import streamlit as st
import streamlit_scrollable_textbox as stx  # type: ignore
import yaml
from humanize import naturaltime

from open_notebook.domain.notebook import Source
from open_notebook.utils import surreal_clean
from pages.stream_app.utils import run_patterns


def source_panel(source_id: str, modal=False):
    source: Source = Source.get(source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")

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
            if source.asset and source.asset.url:
                from_src = f"from URL: {source.asset.url}"
            elif source.asset and source.asset.file_path:
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
                        st.rerun(scope="fragment" if modal else "app")

        with c2:
            with open("transformations.yaml", "r") as file:
                transformations = yaml.safe_load(file)
                for transformation in transformations["source_insights"]:
                    if st.button(
                        transformation["name"], help=transformation["description"]
                    ):
                        result = run_patterns(
                            source.full_text, transformation["patterns"]
                        )
                        source.add_insight(
                            transformation["insight_type"], surreal_clean(result)
                        )
                        st.rerun(scope="fragment" if modal else "app")

            if st.button(
                "Embed vectors",
                icon="🦾",
                disabled=source.embedded_chunks > 0,
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
