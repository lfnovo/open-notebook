import streamlit as st
from langchain_core.runnables import RunnableConfig

from open_notebook.domain.notebook import Note, Source
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.plugins.podcasts import PodcastConfig
from open_notebook.utils import token_count
from stream_app.note import make_note_from_chat


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


def chat_sidebar(session_id):
    context = build_context(session_id=session_id)
    tokens = token_count(str(context) + str(st.session_state[session_id]["messages"]))
    chat_tab, podcast_tab = st.tabs(["Chat", "Podcast"])
    with st.expander(f"Context ({tokens} tokens), {len(str(context))} chars"):
        st.json(context)
    with podcast_tab:
        with st.container(border=True):
            podcast_configs = PodcastConfig.get_all()
            podcast_config_names = [pd.name for pd in podcast_configs]
            if len(podcast_configs) == 0:
                st.warning("No podcast configurations found")
            else:
                template = st.selectbox("Pick a template", podcast_config_names)
                selected_template = next(
                    filter(lambda x: x.name == template, podcast_configs)
                )
                episode_name = st.text_input("Episode Name")
                instructions = st.text_area(
                    "Instructions", value=selected_template.user_instructions
                )
                if len(context.get("note", [])) + len(context.get("source", [])) == 0:
                    st.warning(
                        "No notes or sources found in context. You don't want a boring podcast, right? So, add some context first."
                    )
                else:
                    if st.button("Generate"):
                        with st.spinner("Go grab a coffee, almost there..."):
                            selected_template.generate_episode(
                                episode_name=episode_name,
                                text=context,
                                instructions=instructions,
                            )
                        st.success("Episode generated successfully")
            st.page_link("pages/5_🎙️_Podcasts.py", label="🎙️ Go to Podcasts")
    with chat_tab:
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
                            make_note_from_chat(
                                content=msg.content,
                                notebook_id=st.session_state[session_id]["notebook"].id,
                            )
                            st.rerun()
