import streamlit as st

from api.models_service import ModelsService
from api.notebook_service import notebook_service
from api.notes_service import notes_service
from api.search_service import search_service
from pages.components.model_selector import model_selector
from pages.stream_app.utils import convert_source_references, setup_page

# Initialize service instances
models_service = ModelsService()

setup_page("🔍 Search")

ask_tab, search_tab = st.tabs(["Ask Your Knowledge Base (beta)", "Search"])

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

if "ask_results" not in st.session_state:
    st.session_state["ask_results"] = {}


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
    default_models = models_service.get_default_models()
    default_model = default_models.default_chat_model
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
    embedding_model = default_models.default_embedding_model
    if not embedding_model:
        st.warning(
            "You can't use this feature because you have no embedding model selected. Please set one up in the Models page."
        )
    ask_bt = st.button("Ask") if embedding_model else None
    placeholder = st.container()

    if ask_bt:
        placeholder.write(f"Searching for {question}")
        st.session_state["ask_results"]["question"] = question
        st.session_state["ask_results"]["answer"] = None

        with st.spinner("Processing your question..."):
            try:
                result = search_service.ask_knowledge_base(
                    question=question,
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )

                if result.get("answer"):
                    st.session_state["ask_results"]["answer"] = result["answer"]
                    with placeholder.container(border=True):
                        st.markdown(convert_source_references(result["answer"]))
                else:
                    placeholder.error("No answer generated")

            except Exception as e:
                placeholder.error(f"Error processing question: {str(e)}")

    if st.session_state["ask_results"].get("answer"):
        with st.container(border=True):
            with st.form("save_note_form"):
                notebook = st.selectbox(
                    "Notebook",
                    notebook_service.get_all_notebooks(),
                    format_func=lambda x: x.name,
                )
                if st.form_submit_button("Save Answer as Note"):
                    notes_service.create_note(
                        title=st.session_state["ask_results"]["question"],
                        content=st.session_state["ask_results"]["answer"],
                        note_type="ai",
                        notebook_id=notebook.id,
                    )
                    st.success("Note saved successfully")


with search_tab:
    with st.container(border=True):
        st.subheader("🔍 Search")
        st.caption("Search your knowledge base for specific keywords or concepts")
        search_term = st.text_input("Search", "")
        if not embedding_model:
            st.warning(
                "You can't use vector search because you have no embedding model selected. Only text search will be available."
            )
            search_type = "Text Search"
        else:
            search_type = st.radio("Search Type", ["Text Search", "Vector Search"])
        search_sources = st.checkbox("Search Sources", value=True)
        search_notes = st.checkbox("Search Notes", value=True)
        if st.button("Search"):
            st.write(f"Searching for {search_term}")
            search_type_api = "text" if search_type == "Text Search" else "vector"
            st.session_state["search_results"] = search_service.search(
                query=search_term,
                search_type=search_type_api,
                limit=100,
                search_sources=search_sources,
                search_notes=search_notes,
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
