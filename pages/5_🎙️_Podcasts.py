import streamlit as st
from streamlit_tags import st_tags

from open_notebook.plugins.podcasts import (
    PodcastConfig,
    PodcastEpisode,
    conversation_styles,
    dialogue_structures,
    engagement_techniques,
    participant_roles,
)

episodes_tab, templates_tab = st.tabs(["Episodes", "Templates"])

with episodes_tab:
    episodes = PodcastEpisode.get_all()
    for episode in episodes:
        st.json(episode.model_dump())
    else:
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
        pd_cfg["person1_role"] = st.text_input("Person 1 role")
        st.caption(f"Suggestions:{', '.join(participant_roles)}")
        pd_cfg["person2_role"] = st.text_input("Person 2 role")
        pd_cfg["conversation_style"] = st_tags(
            ["a"], conversation_styles, "Conversation Style"
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
        pd_cfg["provider"] = st.selectbox("Provider", ["openai", "elevenlabs", "edge"])
        pd_cfg["voice1"] = st.text_input("Voice 1")
        pd_cfg["voice2"] = st.text_input("Voice 2")
        pd_cfg["model"] = st.text_input("Model")
        if st.button("Save"):
            pd = PodcastConfig(**pd_cfg)
            pd.save()
            st.success("Saved")

    for pd_config in PodcastConfig.get_all():
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
            pd_config.provider = st.selectbox(
                "Provider",
                ["openai", "elevenlabs", "edge"],
                index=["openai", "elevenlabs", "edge"].index(pd_config.provider),
                key=f"provider_{pd_config.id}",
            )
            pd_config.voice1 = st.text_input(
                "Voice 1", value=pd_config.voice1, key=f"voice1_{pd_config.id}"
            )
            pd_config.voice2 = st.text_input(
                "Voice 2", value=pd_config.voice2, key=f"voice2_{pd_config.id}"
            )
            pd_config.model = st.text_input(
                "Model", value=pd_config.model, key=f"model_{pd_config.id}"
            )

            if st.button("Save Config", key=f"btn_save{pd_config.id}"):
                pd_config.save()
                st.rerun()

            if st.button("Delete Config", key=f"btn_delete{pd_config.id}"):
                pd_config.delete()
                st.rerun()
