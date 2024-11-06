from typing import Dict, List

import streamlit as st
from streamlit_tags import st_tags

from open_notebook.domain.models import Model
from open_notebook.plugins.podcasts import (
    PodcastConfig,
    PodcastEpisode,
    conversation_styles,
    dialogue_structures,
    engagement_techniques,
    participant_roles,
)
from pages.stream_app.utils import setup_page

setup_page("🎙️ Podcasts")

text_to_speech_models = Model.get_models_by_type("text_to_speech")


provider_models: Dict[str, List[str]] = {}

for model in text_to_speech_models:
    if model.provider not in provider_models:
        provider_models[model.provider] = []
    provider_models[model.provider].append(model.name)


if len(text_to_speech_models) == 0:
    st.error("No text to speech models found. Please set one up in the Settings page.")
    st.stop()

episodes_tab, templates_tab = st.tabs(["Episodes", "Templates"])

with episodes_tab:
    episodes = PodcastEpisode.get_all(order_by="created desc")
    for episode in episodes:
        with st.container(border=True):
            episode_name = episode.name if episode.name else "No Name"
            st.markdown(f"**{episode.template} - {episode_name}**")
            # st.caption(naturaltime(episode.created))
            st.write(f"Instructions: {episode.instructions}")
            try:
                st.audio(episode.audio_file, format="audio/mpeg", loop=True)
            except Exception as e:
                st.write("No audio file found")
                st.error(e)
            with st.expander("Source Content"):
                st.code(episode.text)
            if st.button("Delete Episode", key=f"btn_delete{episode.id}"):
                episode.delete()
                st.rerun()
    if len(episodes) == 0:
        st.write("No episodes yet")
with templates_tab:
    st.subheader("Podcast Templates")
    st.markdown("")
    with st.expander("**Create new Template**"):
        pd_cfg = {}
        pd_cfg["name"] = st.text_input("Template Name")
        pd_cfg["podcast_name"] = st.text_input("Podcast Name")
        pd_cfg["podcast_tagline"] = st.text_input("Podcast Tagline")
        pd_cfg["output_language"] = st.text_input("Language", value="English")
        pd_cfg["user_instructions"] = st.text_input(
            "User Instructions",
            help="Any additional intructions to pass to the LLM that will generate the transcript",
        )
        pd_cfg["person1_role"] = st.text_input("Person 1 role")
        st.caption(f"Suggestions:{', '.join(participant_roles)}")
        pd_cfg["person2_role"] = st.text_input("Person 2 role")
        pd_cfg["conversation_style"] = st_tags(
            [], conversation_styles, "Conversation Style"
        )
        st.caption(f"Suggestions:{', '.join(conversation_styles)}")
        pd_cfg["engagement_technique"] = st_tags(
            [], engagement_techniques, "Engagement Techniques"
        )
        st.caption(f"Suggestions:{', '.join(engagement_techniques)}")
        pd_cfg["dialogue_structure"] = st_tags(
            [], dialogue_structures, "Dialogue Structure"
        )
        st.caption(f"Suggestions:{', '.join(dialogue_structures)}")
        pd_cfg["wordcount"] = st.slider(
            "Word Count", min_value=400, max_value=6000, step=50
        )
        pd_cfg["creativity"] = st.slider(
            "Creativity", min_value=0.0, max_value=1.0, step=0.05
        )
        pd_cfg["ending_message"] = st.text_input(
            "Ending Message", placeholder="Thank you for listening!"
        )
        pd_cfg["provider"] = st.selectbox("Provider", provider_models.keys())
        pd_cfg["voice1"] = st.text_input(
            "Voice 1", help="You can use Elevenlabs voice ID"
        )
        st.markdown(
            "[Open AI voices](https://platform.openai.com/docs/guides/text-to-speech)"
        )
        pd_cfg["voice2"] = st.text_input(
            "Voice 2", help="You can use Elevenlabs voice ID"
        )

        pd_cfg["model"] = st.selectbox("Model", provider_models[pd_cfg["provider"]])
        st.caption(
            "OpenAI: tts-1 or tts-1-hd, Elevenlabs: eleven_multilingual_v2, eleven_turbo_v2_5"
        )
        if st.button("Save"):
            try:
                pd = PodcastConfig(**pd_cfg)
                pd_cfg = {}
                pd.save()
                st.rerun()
            except Exception as e:
                st.error(e)
                st.exception(e)

    for pd_config in PodcastConfig.get_all(order_by="created desc"):
        with st.expander(pd_config.name):
            pd_config.name = st.text_input(
                "Template Name", value=pd_config.name, key=f"name_{pd_config.id}"
            )
            pd_config.podcast_name = st.text_input(
                "Podcast Name",
                value=pd_config.podcast_name,
                key=f"podcast_name_{pd_config.id}",
            )
            pd_config.podcast_tagline = st.text_input(
                "Podcast Tagline",
                value=pd_config.podcast_tagline,
                key=f"podcast_tagline_{pd_config.id}",
            )
            pd_config.user_instructions = st.text_input(
                "User Instructions",
                value=pd_config.user_instructions,
                help="Any additional intructions to pass to the LLM that will generate the transcript",
                key=f"user_instructions_{pd_config.id}",
            )

            pd_config.output_language = st.text_input(
                "Language",
                value=pd_config.output_language,
                key=f"output_language_{pd_config.id}",
            )
            pd_config.person1_role = st.text_input(
                "Person 1 role",
                value=pd_config.person1_role,
                key=f"person1_role_{pd_config.id}",
            )
            st.caption(f"Suggestions:{', '.join(participant_roles)}")
            pd_config.person2_role = st.text_input(
                "Person 2 role",
                value=pd_config.person2_role,
                key=f"person2_role_{pd_config.id}",
            )
            pd_config.conversation_style = st_tags(
                pd_config.conversation_style,
                conversation_styles,
                "Conversation Style",
                key=f"conversation_style_{pd_config.id}",
            )
            st.caption(f"Suggestions:{', '.join(conversation_styles)}")
            pd_config.engagement_technique = st_tags(
                pd_config.engagement_technique,
                engagement_techniques,
                "Engagement Techniques",
                key=f"engagement_technique_{pd_config.id}",
            )
            st.caption(f"Suggestions:{', '.join(engagement_techniques)}")
            pd_config.dialogue_structure = st_tags(
                pd_config.dialogue_structure,
                dialogue_structures,
                "Dialogue Structure",
                key=f"dialogue_structure_{pd_config.id}",
            )
            st.caption(f"Suggestions:{', '.join(dialogue_structures)}")
            pd_config.wordcount = st.slider(
                "Word Count",
                min_value=400,
                max_value=6000,
                step=50,
                value=pd_config.wordcount,
                key=f"wordcount_{pd_config.id}",
            )
            pd_config.creativity = st.slider(
                "Creativity",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                value=pd_config.creativity,
                key=f"creativity_{pd_config.id}",
            )
            pd_config.ending_message = st.text_input(
                "Ending Message",
                value=pd_config.ending_message,
                placeholder="Thank you for listening!",
                key=f"ending_message_{pd_config.id}",
            )
            pd_config.provider = st.selectbox(
                "Provider",
                list(provider_models.keys()),
                index=list(provider_models.keys()).index(pd_config.provider),
                key=f"provider_{pd_config.id}",
            )
            pd_config.voice1 = st.text_input(
                "Voice 1",
                value=pd_config.voice1,
                key=f"voice1_{pd_config.id}",
                help="You can use Elevenlabs voice ID",
            )
            st.markdown(
                "[Open AI voices](https://platform.openai.com/docs/guides/text-to-speech)"
            )
            pd_config.voice2 = st.text_input(
                "Voice 2",
                value=pd_config.voice2,
                key=f"voice2_{pd_config.id}",
                help="You can use Elevenlabs voice ID",
            )
            if pd_config.model not in provider_models[pd_config.provider]:
                st.warning(f"Model {pd_config.model} not setup. Changing to default.")
                index = 0
            else:
                index = provider_models[pd_config.provider].index(pd_config.model)
            pd_config.model = st.selectbox(
                "Model",
                provider_models[pd_config.provider],
                index=index,
                key=f"model_{pd_config.id}",
            )
            st.caption(
                "OpenAI: tts-1 or tts-1-hd, Elevenlabs: eleven_multilingual_v2, eleven_turbo_v2_5"
            )

            if st.button("Save Config", key=f"btn_save{pd_config.id}"):
                try:
                    pd_config.save()
                    st.toast("Podcast template saved")
                except Exception as e:
                    st.error(e)

            if st.button("Duplicate Config", key=f"btn_duplicate{pd_config.id}"):
                pd_config.name = f"{pd_config.name} - Copy"
                pd_config.id = None
                pd_config.save()
                st.rerun()

            if st.button("Delete Config", key=f"btn_delete{pd_config.id}"):
                pd_config.delete()
                st.rerun()
