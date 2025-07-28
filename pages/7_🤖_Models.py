import os

import nest_asyncio

nest_asyncio.apply()

import streamlit as st
from esperanto import AIFactory

from api.models_service import models_service
from pages.components.model_selector import model_selector
from pages.stream_app.utils import setup_page

setup_page(
    "🤖 Models",
    only_check_mandatory_models=False,
    stop_on_model_error=False,
    skip_model_check=True,
)


st.title("🤖 Models")

provider_status = {}

model_types = [
    # "vision",
    "language",
    "embedding",
    "text_to_speech",
    "speech_to_text",
]


def check_available_providers():
    provider_status["ollama"] = os.environ.get("OLLAMA_API_BASE") is not None
    provider_status["openai"] = os.environ.get("OPENAI_API_KEY") is not None
    provider_status["groq"] = os.environ.get("GROQ_API_KEY") is not None
    provider_status["xai"] = os.environ.get("XAI_API_KEY") is not None
    provider_status["vertex"] = (
        os.environ.get("VERTEX_PROJECT") is not None
        and os.environ.get("VERTEX_LOCATION") is not None
        and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
    )
    provider_status["google"] = (
        os.environ.get("GOOGLE_API_KEY") is not None
        or os.environ.get("GEMINI_API_KEY") is not None
    )
    provider_status["openrouter"] = os.environ.get("OPENROUTER_API_KEY") is not None
    provider_status["anthropic"] = os.environ.get("ANTHROPIC_API_KEY") is not None
    provider_status["elevenlabs"] = os.environ.get("ELEVENLABS_API_KEY") is not None
    provider_status["voyage"] = os.environ.get("VOYAGE_API_KEY") is not None
    provider_status["azure"] = (
        os.environ.get("AZURE_OPENAI_API_KEY") is not None
        and os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
        and os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") is not None
        and os.environ.get("AZURE_OPENAI_API_VERSION") is not None
    )
    provider_status["mistral"] = os.environ.get("MISTRAL_API_KEY") is not None
    provider_status["deepseek"] = os.environ.get("DEEPSEEK_API_KEY") is not None
    provider_status["openai-compatible"] = (
        os.environ.get("OPENAI_COMPATIBLE_BASE_URL") is not None
    )
    available_providers = [k for k, v in provider_status.items() if v]
    unavailable_providers = [k for k, v in provider_status.items() if not v]

    return available_providers, unavailable_providers


default_models = models_service.get_default_models()
all_models = models_service.get_all_models()
esperanto_available_providers = AIFactory.get_available_providers()


st.subheader("Provider Availability")
st.markdown(
    "Below, you'll find all AI providers supported and their current availability status. To enable more providers, you need to setup some of their ENV Variables. Please check [the documentation](https://github.com/lfnovo/open-notebook/blob/main/docs/models.md) for instructions on how to do so."
)
available_providers, unavailable_providers = check_available_providers()
with st.expander("Available Providers"):
    st.write(available_providers)
with st.expander("Unavailable Providers"):
    st.write(unavailable_providers)

st.divider()


# Helper function to add model with auto-save
def add_model_form(model_type, container_key, configured_providers):
    # Get providers that Esperanto supports for this model type
    esperanto_providers = esperanto_available_providers.get(model_type, [])
    # Filter to only show providers that have API keys configured
    available_providers = [p for p in esperanto_providers if p in configured_providers]
    # Sort providers alphabetically for easier navigation
    available_providers.sort()

    # Remove perplexity from available_providers if it exists
    if "perplexity" in available_providers:
        available_providers.remove("perplexity")

    if not available_providers:
        st.info(f"No providers available for {model_type}")
        return

    st.markdown("**Add New Model**")

    with st.form(key=f"add_{model_type}_{container_key}"):
        provider = st.selectbox(
            "Provider",
            available_providers,
            key=f"provider_{model_type}_{container_key}",
        )

        model_name = st.text_input(
            "Model Name",
            key=f"name_{model_type}_{container_key}",
            help="gpt-4o-mini, claude, gemini, llama3, etc. For azure, use the deployment_name as the model_name",
        )

        if st.form_submit_button("Add Model"):
            if model_name:
                models_service.create_model(
                    name=model_name, provider=provider, model_type=model_type
                )
                st.success("Model added!")
                st.rerun()


# Helper function to handle default model selection with auto-save
def handle_default_selection(
    label, key, current_value, help_text, model_type, caption=None
):
    selected_model = model_selector(
        label,
        key,
        selected_id=current_value,
        help=help_text,
        model_type=model_type,
    )
    # Auto-save when selection changes
    if selected_model and (not current_value or selected_model.id != current_value):
        setattr(default_models, key, selected_model.id)
        models_service.update_default_models(default_models)
        # Model defaults are automatically refreshed through the API service
        st.toast(f"Default {model_type} model set to {selected_model.name}")
    elif not selected_model and current_value:
        setattr(default_models, key, None)
        models_service.update_default_models(default_models)
        # Model defaults are automatically refreshed through the API service
        st.toast(f"Default {model_type} model removed")

    if caption:
        st.caption(caption)
    return selected_model


# Group models by type
models_by_type = {
    "language": [],
    "embedding": [],
    "text_to_speech": [],
    "speech_to_text": [],
}

for model in all_models:
    if model.type in models_by_type:
        models_by_type[model.type].append(model)


st.markdown("""
**Model Management Guide:** For optimal performance, refer to [Which model to choose?](https://github.com/lfnovo/open-notebook/blob/main/docs/models.md) 
You can test models in the [Transformations](Transformations) page.
""")

# Language Models Section
st.subheader("🗣️ Language Models")
with st.container(border=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Configured Models**")
        language_models = models_by_type["language"]
        if language_models:
            for model in language_models:
                subcol1, subcol2 = st.columns([4, 1])
                with subcol1:
                    st.markdown(f"• {model.provider}/{model.name}")
                with subcol2:
                    if st.button(
                        "🗑️", key=f"delete_lang_{model.id}", help="Delete model"
                    ):
                        models_service.delete_model(model.id)
                        st.rerun()
        else:
            st.info("No language models configured")

    with col2:
        add_model_form("language", "main", available_providers)

    st.markdown("**Default Model Assignments**")
    col1, col2 = st.columns(2)

    with col1:
        handle_default_selection(
            "Chat Model",
            "default_chat_model",
            default_models.default_chat_model,
            "Used for chat conversations",
            "language",
            "Pick the one that vibes with you.",
        )

        handle_default_selection(
            "Tools Model",
            "default_tools_model",
            default_models.default_tools_model,
            "Used for calling tools - use OpenAI or Anthropic",
            "language",
            "Recommended: gpt-4o, claude, qwen3, etc.",
        )

    with col2:
        handle_default_selection(
            "Transformation Model",
            "default_transformation_model",
            default_models.default_transformation_model,
            "Used for summaries, insights, etc.",
            "language",
            "Can use cheaper models: gpt-4o-mini, llama3, gemma3, etc.",
        )

        handle_default_selection(
            "Large Context Model",
            "large_context_model",
            default_models.large_context_model,
            "Used for large context processing",
            "language",
            "Recommended: Gemini models",
        )

    # Show warning if mandatory language models are missing
    if (
        not default_models.default_chat_model
        or not default_models.default_transformation_model
    ):
        st.warning(
            "⚠️ Please select a Chat Model and Transformation Model - these are required for Open Notebook to function properly."
        )
    elif not default_models.default_tools_model:
        st.info(
            "💡 Consider selecting a Tools Model for better tool calling capabilities (recommended: OpenAI or Anthropic models)."
        )

# Embedding Models Section
st.subheader("🔍 Embedding Models")
with st.container(border=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Configured Models**")
        embedding_models = models_by_type["embedding"]
        if embedding_models:
            for model in embedding_models:
                subcol1, subcol2 = st.columns([4, 1])
                with subcol1:
                    st.markdown(f"• {model.provider}/{model.name}")
                with subcol2:
                    if st.button(
                        "🗑️", key=f"delete_emb_{model.id}", help="Delete model"
                    ):
                        models_service.delete_model(model.id)
                        st.rerun()
        else:
            st.info("No embedding models configured")

        handle_default_selection(
            "Default Embedding Model",
            "default_embedding_model",
            default_models.default_embedding_model,
            "Used for semantic search and embeddings",
            "embedding",
        )
        st.warning("⚠️ Changing embedding models requires regenerating all embeddings")

        # Show warning if no default embedding model is selected
        if not default_models.default_embedding_model:
            st.warning(
                "⚠️ Please select a default Embedding Model - this is required for search functionality."
            )

    with col2:
        add_model_form("embedding", "main", available_providers)

# Text-to-Speech Models Section
st.subheader("🎙️ Text-to-Speech Models")
with st.container(border=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Configured Models**")
        tts_models = models_by_type["text_to_speech"]
        if tts_models:
            for model in tts_models:
                subcol1, subcol2 = st.columns([4, 1])
                with subcol1:
                    st.markdown(f"• {model.provider}/{model.name}")
                with subcol2:
                    if st.button(
                        "🗑️", key=f"delete_tts_{model.id}", help="Delete model"
                    ):
                        models_service.delete_model(model.id)
                        st.rerun()
        else:
            st.info("No text-to-speech models configured")

        handle_default_selection(
            "Default TTS Model",
            "default_text_to_speech_model",
            default_models.default_text_to_speech_model,
            "Used for podcasts and audio generation",
            "text_to_speech",
            "Can be overridden per podcast",
        )

        # Show info if no default TTS model is selected
        if not default_models.default_text_to_speech_model:
            st.info("ℹ️ Select a default TTS model to enable podcast generation.")

    with col2:
        add_model_form("text_to_speech", "main", available_providers)

# Speech-to-Text Models Section
st.subheader("🎤 Speech-to-Text Models")
with st.container(border=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Configured Models**")
        stt_models = models_by_type["speech_to_text"]
        if stt_models:
            for model in stt_models:
                subcol1, subcol2 = st.columns([4, 1])
                with subcol1:
                    st.markdown(f"• {model.provider}/{model.name}")
                with subcol2:
                    if st.button(
                        "🗑️", key=f"delete_stt_{model.id}", help="Delete model"
                    ):
                        models_service.delete_model(model.id)
                        st.rerun()
        else:
            st.info("No speech-to-text models configured")

        handle_default_selection(
            "Default STT Model",
            "default_speech_to_text_model",
            default_models.default_speech_to_text_model,
            "Used for audio transcriptions",
            "speech_to_text",
        )

        # Show info if no default STT model is selected
        if not default_models.default_speech_to_text_model:
            st.info(
                "ℹ️ Select a default STT model to enable audio transcription features."
            )

    with col2:
        add_model_form("speech_to_text", "main", available_providers)
