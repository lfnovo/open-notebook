import streamlit as st
from langchain_core.runnables import RunnableConfig

from open_notebook.domain import Note, Source
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.utils import token_count


# todo: build a smarter, more robust context manager function
def build_context(session_id):
    st.session_state[session_id]["context"] = dict(note=[], source=[])

    for id, status in st.session_state[session_id]["context_config"].items():
        if not id:
            continue

        item_type, item_id = id.split(":")
        if item_type not in ["note", "source"]:
            continue

        if "not in" in status:
            continue

        if item_type == "note":
            item: Note = Note.get(id)
        elif item_type == "source":
            item: Source = Source.get(id)
        else:
            continue

        if not item:
            continue
        if "summary" in status:
            st.session_state[session_id]["context"][item_type] += [
                item.get_context(context_size="short")
            ]
        elif "full content" in status:
            st.session_state[session_id]["context"][item_type] += [
                item.get_context(context_size="long")
            ]

    return st.session_state[session_id]["context"]


def execute_chat(txt_input, session_id):
    current_state = st.session_state[session_id]
    current_state["messages"] += [txt_input]
    result = chat_graph.invoke(
        input=current_state,
        config=RunnableConfig(configurable={"thread_id": session_id}),
    )
    return result


# todo: se eu for usar o token count, preciso deixar configuravel
# seria bom ter um total de tokens no admin em algum lugar
def chat_sidebar(session_id):
    context = build_context(session_id=session_id)
    tokens = token_count(str(context) + str(st.session_state[session_id]["messages"]))
    with st.container(border=True):
        request = st.chat_input("Enter your question")
        # removing for now since it's not multi-model capable right now
        st.caption(f"Total tokens: {tokens}")
        if request:
            response = execute_chat(txt_input=request, session_id=session_id)
            st.session_state[session_id]["messages"] = response["messages"]

        for msg in st.session_state[session_id]["messages"][::-1]:
            if msg.type not in ["human", "ai"]:
                continue
            if not msg.content:
                continue

            with st.chat_message(name=msg.type):
                st.write(msg.content)
                if msg.type == "ai":
                    if st.button("💾 New Note", key=f"render_save_{msg.id}"):
                        title = "New Note"
                        content = msg.content
                        note = Note(
                            title=title,
                            content=content,
                            note_type="ai",
                        )
                        note.save()
                        note.add_to_notebook(
                            st.session_state[session_id]["notebook"].id
                        )
                        st.rerun()
