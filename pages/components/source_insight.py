import nest_asyncio
import streamlit as st

from api.insights_service import insights_service
from api.sources_service import sources_service
from open_notebook.domain.notebook import SourceInsight

nest_asyncio.apply()


def source_insight_panel(source, notebook_id=None):
    si: SourceInsight = insights_service.get_insight(source)
    if not si:
        raise ValueError(f"insight not found {source}")
    st.subheader(si.insight_type)
    with st.container(border=True):
        # Get source information using the source_id from the insight
        source_id = si.source_id
        if source_id is None:
            raise ValueError("Source insight is missing source reference")
        source_obj = sources_service.get_source(source_id)
        url = f"Navigator?object_id={source_obj.id}"
        st.markdown("**Original Source**")
        st.markdown(f"{source_obj.title} [link](%s)" % url)
    st.markdown(si.content)
    if st.button("Delete", type="primary", key=f"delete_insight_{si.id or 'new'}"):
        insights_service.delete_insight(si.id)
        st.rerun()
