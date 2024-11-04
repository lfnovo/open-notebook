import streamlit as st

from open_notebook.domain.models import Model
from open_notebook.domain.notebook import text_search, vector_search
from open_notebook.graphs.rag import graph as rag_graph
from pages.stream_app.utils import setup_page

setup_page("🔍 Search")

ask_tab, search_tab = st.tabs(["Ask Your Knowledge Base (beta)", "Search"])

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []


def results_card(item):
    score = item.get("relevance", item.get("similarity", item.get("score", 0)))
    with st.expander(f"[{score:.2f}] **{item['title']}**"):
        st.markdown(f"**{item['content']}**")
        st.write(item["id"])
        st.write(item["parent_id"])


with ask_tab:
    st.subheader("Ask Your Knowledge Base (beta)")
    st.caption(
        "The LLM will answer your query based on the documents in your knowledge base. "
    )
    st.warning(
        "This functionality requires the use of Tools and, at this moment, works well with Open AI and Anthropic models only."
    )
    question = st.text_input("Question", "")
    models = Model.get_models_by_type("language")
    model: Model = st.selectbox("Model", models, format_func=lambda x: x.name)
    if st.button("Ask"):
        st.write(f"Searching for {question}")
        messages = [question]
        rag_results = rag_graph.invoke(
            dict(
                messages=messages
            ),  # config=dict(configurable=dict(model_id=model.id))
        )
        st.markdown(rag_results["messages"][-1].content)
        with st.expander("Details (for debugging)"):
            st.json(rag_results)

with search_tab:
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
                st.session_state["search_results"] = vector_search(
                    search_term, 100, search_sources, search_notes
                )
        for item in st.session_state["search_results"]:
            results_card(item)
