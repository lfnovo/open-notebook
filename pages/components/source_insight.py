import asyncio

import nest_asyncio
import streamlit as st

nest_asyncio.apply()

from open_notebook.domain.notebook import SourceInsight


def source_insight_panel(source, notebook_id=None):
    si: SourceInsight = asyncio.run(SourceInsight.get(source))
    if not si:
        raise ValueError(f"insight not found {source}")
    st.subheader(si.insight_type)
    with st.container(border=True):
        source_obj = asyncio.run(si.get_source())
        url = f"Navigator?object_id={source_obj.id}"
        st.markdown("**Original Source**")
        st.markdown(f"{source_obj.title} [link](%s)" % url)
    st.markdown(si.content)
    if st.button("Delete", type="primary", key=f"delete_insight_{si.id or 'new'}"):
        asyncio.run(si.delete())
        st.rerun()
