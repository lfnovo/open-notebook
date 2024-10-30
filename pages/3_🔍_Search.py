import streamlit as st

from open_notebook.domain.notebook import text_search, vector_search
from open_notebook.utils import get_embedding
from stream_app.note import note_list_item
from stream_app.source import source_list_item
from stream_app.utils import version_sidebar

st.set_page_config(
    layout="wide", page_title="🔍 Search", initial_sidebar_state="expanded"
)
version_sidebar()

# search_tab, ask_tab = st.tabs(["Search", "Ask"])
# notebooks = Notebook.get_all()

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

# with search_tab:
with st.container(border=True):
    st.subheader("🔍 Search")
    st.caption("Search your knowledge base for specific keywords or concepts")
    search_term = st.text_input("Search", "")
    search_type = st.radio("Search Type", ["Text Search", "Vector Search"])
    search_sources = st.checkbox("Search Sources", value=True)
    search_notes = st.checkbox("Search Notes", value=True)
    if st.button("Search"):
        if search_type == "Text Search":
            st.write(f"Searching for {search_term}")
            st.session_state["search_results"] = text_search(
                search_term, 100, search_sources, search_notes
            )
        elif search_type == "Vector Search":
            st.write(f"Searching for {search_term}")
            embed_query = get_embedding(search_term)
            st.session_state["search_results"] = vector_search(
                embed_query, 100, search_sources, search_notes
            )
    for item in st.session_state["search_results"]:
        score = item.get("relevance", item.get("similarity", 0))
        if item.get("item_id"):
            if "source:" in item["item_id"]:
                source_list_item(item["item_id"], score)
            elif "note:" in item["item_id"]:
                note_list_item(item["item_id"], score)

# coming soon
# with ask_tab:
#     with st.form(key="ask_form"):
#         st.subheader("Ask Your Knowledge Base")
#         st.caption("Let the LLM formulate an answer based on your query")
#         question = st.text_input("Your question", "")

#         notebooks = st.multiselect(
#             "Notebooks",
#             notebooks,
#             notebooks,
#             format_func=lambda x: x.name,
#         )
#         search_sources = st.multiselect(
#             "Use Sources",
#             ["Sources", "Notes"],
#             ["Sources", "Notes"],
#         )
#         if st.form_submit_button("Search"):
#             st.write(f"Searching for {search_term}")
