import streamlit as st

from open_notebook.domain.models import Model
from open_notebook.domain.notebook import text_search, vector_search
from open_notebook.graphs.ask import graph as ask_graph
from pages.stream_app.utils import convert_source_references, setup_page

setup_page("🔍 Search")

ask_tab, search_tab = st.tabs(["Ask Your Knowledge Base (beta)", "Search"])

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []


def results_card(item):
    score = item.get("relevance", item.get("similarity", item.get("score", 0)))
    with st.container(border=True):
        st.markdown(
            f"[{score:.2f}] **[{item['title']}](/?object_id={item['parent_id']})**"
        )
        with st.expander("Matches"):
            for match in item["matches"]:
                st.markdown(match)


with ask_tab:
    st.subheader("Ask Your Knowledge Base (beta)")
    st.caption(
        "The LLM will answer your query based on the documents in your knowledge base. "
    )
    question = st.text_input("Question", "")
    models = Model.get_models_by_type("language")
    strategy_model: Model = st.selectbox(
        "Query Strategy Model",
        models,
        format_func=lambda x: x.name,
        help="This is the LLM that will be responsible for strategizing the search",
    )
    answer_model: Model = st.selectbox(
        "Indivual Answer Model",
        models,
        format_func=lambda x: x.name,
        help="This is the LLM that will be responsible for processing individual subqueries",
    )
    final_answer_model: Model = st.selectbox(
        "Final Answer Model",
        models,
        format_func=lambda x: x.name,
        help="This is the LLM that will be responsible for processing the final answer",
    )
    if st.button("Ask"):
        st.write(f"Searching for {question}")
        rag_results = ask_graph.invoke(
            dict(
                question=question,
            ),
            config=dict(
                configurable=dict(
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )
            ),
        )
        st.markdown(convert_source_references(rag_results["final_answer"]))
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
