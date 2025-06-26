import asyncio

import nest_asyncio
import streamlit as st

from open_notebook.domain.models import DefaultModels, model_manager
from open_notebook.domain.notebook import Note, Notebook, text_search, vector_search
from open_notebook.graphs.ask import graph as ask_graph
from pages.components.model_selector import model_selector
from pages.stream_app.utils import convert_source_references, setup_page

nest_asyncio.apply()

setup_page("🔍 Search")

ask_tab, search_tab = st.tabs(["Ask Your Knowledge Base (beta)", "Search"])

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

if "ask_results" not in st.session_state:
    st.session_state["ask_results"] = {}


async def process_ask_query(question, strategy_model, answer_model, final_answer_model):
    async for chunk in ask_graph.astream(
        input=dict(
            question=question,
        ),
        config=dict(
            configurable=dict(
                strategy_model=strategy_model.id,
                answer_model=answer_model.id,
                final_answer_model=final_answer_model.id,
            )
        ),
        stream_mode="updates",
    ):
        yield (chunk)


def results_card(item):
    with st.container(border=True):
        st.markdown(
            f"[{item['final_score']:.2f}] **[{item['title']}](/?object_id={item['parent_id']})**"
        )
        if "matches" in item:
            with st.expander("Matches"):
                for match in item["matches"]:
                    st.markdown(match)


with ask_tab:
    st.subheader("Ask Your Knowledge Base (beta)")
    st.caption(
        "The LLM will answer your query based on the documents in your knowledge base. "
    )
    question = st.text_input("Question", "")
    default_model = DefaultModels().default_chat_model
    strategy_model = model_selector(
        "Query Strategy Model",
        "strategy_model",
        selected_id=default_model,
        model_type="language",
        help="This is the LLM that will be responsible for strategizing the search",
    )
    answer_model = model_selector(
        "Individual Answer Model",
        "answer_model",
        model_type="language",
        selected_id=default_model,
        help="This is the LLM that will be responsible for processing individual subqueries",
    )
    final_answer_model = model_selector(
        "Final Answer Model",
        "final_answer_model",
        model_type="language",
        selected_id=default_model,
        help="This is the LLM that will be responsible for processing the final answer",
    )
    if not model_manager.embedding_model:
        st.warning(
            "You can't use this feature because you have no embedding model selected. Please set one up in the Models page."
        )
    ask_bt = st.button("Ask") if model_manager.embedding_model else None
    placeholder = st.container()

    async def stream_results():
        async for chunk in process_ask_query(
            question, strategy_model, answer_model, final_answer_model
        ):
            if "agent" in chunk:
                with placeholder.expander(
                    f"Agent Strategy: {chunk['agent']['strategy'].reasoning}"
                ):
                    for search in chunk["agent"]["strategy"].searches:
                        st.markdown(f"Searched for: **{search.term}**")
                        st.markdown(f"Instructions: {search.instructions}")
            elif "provide_answer" in chunk:
                for answer in chunk["provide_answer"]["answers"]:
                    with placeholder.expander("Answer"):
                        st.markdown(convert_source_references(answer))
            elif "write_final_answer" in chunk:
                st.session_state["ask_results"]["answer"] = chunk["write_final_answer"][
                    "final_answer"
                ]
                with placeholder.container(border=True):
                    st.markdown(
                        convert_source_references(
                            chunk["write_final_answer"]["final_answer"]
                        )
                    )

    if ask_bt:
        placeholder.write(f"Searching for {question}")
        st.session_state["ask_results"]["question"] = question
        st.session_state["ask_results"]["answer"] = None

        asyncio.run(stream_results())

    if st.session_state["ask_results"].get("answer"):
        with st.container(border=True):
            with st.form("save_note_form"):
                notebook = st.selectbox(
                    "Notebook", Notebook.get_all(), format_func=lambda x: x.name
                )
                if st.form_submit_button("Save Answer as Note"):
                    note = Note(
                        title=st.session_state["ask_results"]["question"],
                        content=st.session_state["ask_results"]["answer"],
                    )
                    note.save()
                    note.add_to_notebook(notebook.id)
                    st.success("Note saved successfully")


with search_tab:
    with st.container(border=True):
        st.subheader("🔍 Search")
        st.caption("Search your knowledge base for specific keywords or concepts")
        search_term = st.text_input("Search", "")
        if not model_manager.embedding_model:
            st.warning(
                "You can't use vector search because you have no embedding model selected. Only text search will be available."
            )
            search_type = "Text Search"
        else:
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

        search_results = st.session_state["search_results"].copy()
        for item in search_results:
            item["final_score"] = item.get(
                "relevance", item.get("similarity", item.get("score", 0))
            )

        # Sort search results by final_score in descending order
        search_results.sort(key=lambda x: x["final_score"], reverse=True)

        for item in search_results:
            results_card(item)
