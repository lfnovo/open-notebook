import streamlit as st

from open_notebook.domain.notebook import SourceInsight


def source_insight_panel(source, notebook_id=None):
    si: SourceInsight = SourceInsight.get(source)
    if not si:
        raise ValueError(f"insight not found {source}")
    st.subheader(si.insight_type)
    with st.container(border=True):
        url = f"Navigator?object_id={si.source.id}"
        st.markdown("**Original Source**")
        st.markdown(f"{si.source.title} [link](%s)" % url)
    st.markdown(si.content)
    if st.button("Delete", type="primary", key=f"delete_insight_{si.id or 'new'}"):
        si.delete()
        st.rerun()
