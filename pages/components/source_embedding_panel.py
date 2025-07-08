import asyncio

import nest_asyncio
import streamlit as st

nest_asyncio.apply()

from open_notebook.domain.notebook import SourceEmbedding


def source_embedding_panel(source_embedding_id):
    si: SourceEmbedding = asyncio.run(SourceEmbedding.get(source_embedding_id))
    if not si:
        raise ValueError(f"Embedding not found {source_embedding_id}")
    with st.container(border=True):
        source_obj = asyncio.run(si.get_source())
        url = f"Navigator?object_id={source_obj.id}"
        st.markdown("**Original Source**")
        st.markdown(f"{source_obj.title} [link](%s)" % url)
    st.markdown(si.content)
    if st.button("Delete", type="primary", key=f"delete_embedding_{si.id or 'new'}"):
        asyncio.run(si.delete())
        st.rerun()
