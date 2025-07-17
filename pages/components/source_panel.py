import streamlit as st
from humanize import naturaltime

from api.insights_service import insights_service
from api.sources_service import SourcesService
from api.transformations_service import TransformationsService
from api.models_service import ModelsService
from pages.stream_app.utils import check_models

# Initialize service instances
sources_service = SourcesService()
transformations_service = TransformationsService()
models_service = ModelsService()


def source_panel(source_id: str, notebook_id=None, modal=False):
    check_models(only_mandatory=False)
    source_with_metadata = sources_service.get_source(source_id)
    if not source_with_metadata:
        raise ValueError(f"Source not found: {source_id}")

    # Now we can access both the source and embedded_chunks directly
    current_title = source_with_metadata.title if source_with_metadata.title else "No Title"
    source_with_metadata.title = st.text_input("Title", value=current_title)
    if source_with_metadata.title != current_title:
        sources_service.update_source(source_with_metadata.source)
        st.toast("Saved new Title")

    process_tab, source_tab = st.tabs(["Process", "Source"])
    with process_tab:
        c1, c2 = st.columns([4, 2])
        with c1:
            title = st.empty()
            if source_with_metadata.title:
                title.subheader(source_with_metadata.title)
            if source_with_metadata.asset and source_with_metadata.asset.url:
                from_src = f"from URL: {source_with_metadata.asset.url}"
            elif source_with_metadata.asset and source_with_metadata.asset.file_path:
                from_src = f"from file: {source_with_metadata.asset.file_path}"
            else:
                from_src = "from text"
            st.caption(f"Created {naturaltime(source_with_metadata.created)}, {from_src}")
            for insight in insights_service.get_source_insights(source_with_metadata.id):
                with st.expander(f"**{insight.insight_type}**"):
                    st.markdown(insight.content)
                    x1, x2 = st.columns(2)
                    if x1.button(
                        "Delete", type="primary", key=f"delete_insight_{insight.id}"
                    ):
                        insights_service.delete_insight(insight.id)
                        st.rerun(scope="fragment" if modal else "app")
                        st.toast("Insight deleted")
                    if notebook_id:
                        if x2.button(
                            "Save as Note", icon="📝", key=f"save_note_{insight.id}"
                        ):
                            insights_service.save_insight_as_note(insight.id, notebook_id)
                            st.toast("Saved as Note. Refresh the Notebook to see it.")

        with c2:
            transformations = transformations_service.get_all_transformations()
            if transformations:
                with st.container(border=True):
                    transformation = st.selectbox(
                        "Run a transformation",
                        transformations,
                        key=f"transformation_{source_with_metadata.id}",
                        format_func=lambda x: x.name,
                    )
                    st.caption(transformation.description if transformation else "")
                    if st.button("Run"):
                        insights_service.create_source_insight(
                            source_id=source_with_metadata.id,
                            transformation_id=transformation.id
                        )
                        st.rerun(scope="fragment" if modal else "app")
            else:
                st.markdown(
                    "No transformations created yet. Create new Transformation to use this feature."
                )

            default_models = models_service.get_default_models()
            embedding_model = default_models.default_embedding_model
            if not embedding_model:
                help = (
                    "No embedding model found. Please, select one on the Models page."
                )
            else:
                help = "This will generate your embedding vectors on the database for powerful search capabilities"

            if not source_with_metadata.embedded_chunks and st.button(
                "Embed vectors",
                icon="🦾",
                help=help,
                disabled=not embedding_model,
            ):
                from api.embedding_service import embedding_service

                result = embedding_service.embed_content(source_with_metadata.id, "source")
                st.success(result.get("message", "Embedding complete"))

            with st.container(border=True):
                st.caption(
                    "Deleting the source will also delete all its insights and embeddings"
                )
                if st.button(
                    "Delete", type="primary", key=f"bt_delete_source_{source_with_metadata.id}"
                ):
                    sources_service.delete_source(source_with_metadata.id)
                    st.rerun()

    with source_tab:
        st.subheader("Content")
        st.markdown(source_with_metadata.full_text)
