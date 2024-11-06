import streamlit as st

from open_notebook.domain.notebook import SourceEmbedding


def source_embedding_panel(source_embedding_id):
    si: SourceEmbedding = SourceEmbedding.get(source_embedding_id)
    if not si:
        raise ValueError(f"Embedding not found {source_embedding_id}")
    with st.container(border=True):
        url = f"Navigator?object_id={si.source.id}"
        st.markdown("**Original Source**")
        st.markdown(f"{si.source.title} [link](%s)" % url)
    st.markdown(si.content)
    if st.button("Delete", type="primary", key=f"delete_embedding_{si.id or 'new'}"):
        si.delete()
        st.rerun()
