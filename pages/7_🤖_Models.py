import os

import streamlit as st
from esperanto import AIFactory

from open_notebook.config import CONFIG
from open_notebook.domain.models import DefaultModels, Model, model_manager
from pages.components.model_selector import model_selector
from pages.stream_app.utils import setup_page

setup_page("🤖 Models", only_check_mandatory_models=False, stop_on_model_error=False)


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
    provider_status["vertexai"] = (
        os.environ.get("VERTEX_PROJECT") is not None
        and os.environ.get("VERTEX_LOCATION") is not None
        and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
    )
    # provider_status["vertexai-anthropic"] = (
    #     os.environ.get("VERTEX_PROJECT") is not None
    #     and os.environ.get("VERTEX_LOCATION") is not None
    #     and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
    # )
    provider_status["gemini"] = os.environ.get("GOOGLE_API_KEY") is not None
    provider_status["openrouter"] = (
        os.environ.get("OPENROUTER_API_KEY") is not None
        and os.environ.get("OPENAI_API_KEY") is not None
        and os.environ.get("OPENROUTER_BASE_URL") is not None
    )
    provider_status["anthropic"] = os.environ.get("ANTHROPIC_API_KEY") is not None
    provider_status["elevenlabs"] = os.environ.get("ELEVENLABS_API_KEY") is not None
    provider_status["voyage"] = os.environ.get("VORAGE_API_KEY") is not None
    provider_status["azure"] = (
        os.environ.get("AZURE_OPENAI_API_KEY") is not None
        and os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
        and os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") is not None
        and os.environ.get("AZURE_OPENAI_API_VERSION") is not None
    )
    provider_status["mistral"] = os.environ.get("MISTRAL_API_KEY") is not None
    provider_status["deepseek"] = os.environ.get("DEEPSEEK_API_KEY") is not None

    available_providers = [k for k, v in provider_status.items() if v]
    unavailable_providers = [k for k, v in provider_status.items() if not v]

    return available_providers, unavailable_providers


def generate_new_models(models, suggested_models):
    # Create a set of existing model keys for efficient lookup
    existing_model_keys = {
        f"{model.provider}-{model.name}-{model.type}" for model in models
    }

    new_models = []

    # Iterate through suggested models by provider
    for provider, types in suggested_models.items():
        # Iterate through each type (language, embedding, etc.)
        for type_, model_list in types.items():
            for model_name in model_list:
                model_key = f"{provider}-{model_name}-{type_}"

                # Check if model already exists
                if model_key not in existing_model_keys:
                    if provider_status.get(provider):
                        new_models.append(
                            {
                                "name": model_name,
                                "type": type_,
                                "provider": provider,
                            }
                        )

    return new_models


default_models = DefaultModels()
all_models = Model.get_all()
esperanto_available_providers = AIFactory.get_available_providers()


st.subheader("Provider Availability")
st.markdown(
    "Below, you'll find all AI providers supported and their current availability status. To enable more providers, you need to setup some of their ENV Variables. Please check [the documentation](https://github.com/lfnovo/open-notebook) for instructions on how to do so."
)
available_providers, unavailable_providers = check_available_providers()
with st.expander("Available Providers"):
    st.write(available_providers)
with st.expander("Unavailable Providers"):
    st.write(unavailable_providers)

st.divider()
st.subheader("Add Model")
st.markdown(
    "Even though a lot of models can be supported, not all will perform optimally. Some are more fit for use in this tool than others. To help you decide which models to use, please refer to [Which model to choose?](https://github.com/lfnovo/open-notebook/blob/main/docs/SETUP.md#which-model-to-choose) for more information. You can also play with some models in the [Transformations](https://try-it-out.open-notebook.com) page to see if they match your needs."
)

available_model_types = esperanto_available_providers.keys()
model_type = st.selectbox(
    "Model Type",
    available_model_types,
    help="Use language for text generation models, text_to_speech for TTS models for generating podcasts, etc.",
)
provider = st.selectbox("Provider", esperanto_available_providers[model_type])

if model_type == "text_to_speech" and provider == "gemini":
    model_name = "gemini-default"
    st.markdown("Gemini models are pre-configured. Using the default model.")
else:
    model_name = st.text_input(
        "Model Name", "", help="gpt-4o-mini, claude, gemini, llama3, etc"
    )
if st.button("Save"):
    model = Model(name=model_name, provider=provider, type=model_type)
    model.save()
    st.success("Saved")

st.divider()
suggested_models = CONFIG.get("suggested_models", [])
recommendations = generate_new_models(all_models, suggested_models)
if len(recommendations) > 0:
    with st.expander("💁‍♂️ Recommended models to get you started.."):
        for recommendation in recommendations:
            st.markdown(
                f"**{recommendation['name']}** ({recommendation['provider']}, {recommendation['type']})"
            )
            if st.button("Add", key=f"add_{recommendation['name']}"):
                new_model = Model(**recommendation)
                new_model.save()
                st.rerun()
st.divider()

st.subheader("Configured Models")
model_types_available = {
    # "vision": False,
    "language": False,
    "embedding": False,
    "text_to_speech": False,
    "speech_to_text": False,
}
for model in all_models:
    model_types_available[model.type] = True
    with st.container(border=True):
        st.markdown(f"{model.name} ({model.provider}, {model.type})")
        if st.button("Delete", key=f"delete_{model.id}"):
            model.delete()
            st.rerun()

for model_type, available in model_types_available.items():
    if not available:
        st.warning(f"No models available for {model_type}")


st.divider()

st.subheader("Select Default Models")
text_generation_models = [model for model in all_models if model.type == "language"]

text_to_speech_models = [
    model for model in all_models if model.type == "text_to_speech"
]

speech_to_text_models = [
    model for model in all_models if model.type == "speech_to_text"
]
vision_models = [model for model in all_models if model.type == "vision"]
embedding_models = [model for model in all_models if model.type == "embedding"]
st.write(
    "In this section, you can select the default models to be used on the various content operations done by Open Notebook. Some of these can be overriden in the different modules."
)
defs = {}
# Handle chat model selection
selected_model = model_selector(
    "Default Chat Model",
    "default_chat_model",
    selected_id=default_models.default_chat_model,
    help="This model will be used for chat.",
    model_type="language",
)
if selected_model:
    default_models.default_chat_model = selected_model.id
st.divider()
# Handle transformation model selection
selected_model = model_selector(
    "Default Transformation Model",
    "default_transformation_model",
    selected_id=default_models.default_transformation_model,
    help="This model will be used for text transformations such as summaries, insights, etc.",
    model_type="language",
)
if selected_model:
    default_models.default_transformation_model = selected_model.id
st.caption("You can use a cheap model here like gpt-4o-mini, llama3, etc.")
st.divider()

# Handle tools model selection
selected_model = model_selector(
    "Default Tools Model",
    "default_tools_model",
    selected_id=default_models.default_tools_model,
    help="This model will be used for calling tools. Currently, it's best to use Open AI and Anthropic for this.",
    model_type="language",
)
if selected_model:
    default_models.default_tools_model = selected_model.id
st.caption("Recommended to use a capable model here, like gpt-4o, claude, etc.")
st.divider()

# Handle large context model selection
selected_model = model_selector(
    "Large Context Model",
    "large_context_model",
    selected_id=default_models.large_context_model,
    help="This model will be used for larger context generation -- recommended: Gemini",
    model_type="language",
)
if selected_model:
    default_models.large_context_model = selected_model.id
st.caption("Recommended to use Gemini models for larger context processing")
st.divider()

# Handle text-to-speech model selection
selected_model = model_selector(
    "Default Text to Speech Model",
    "default_text_to_speech_model",
    selected_id=default_models.default_text_to_speech_model,
    help="This is the default model for converting text to speech (podcasts, etc)",
    model_type="text_to_speech",
)
st.caption("You can override this model on different podcasts")
if selected_model:
    default_models.default_text_to_speech_model = selected_model.id
st.divider()

# Handle speech-to-text model selection
selected_model = model_selector(
    "Default Speech to Text Model",
    selected_id=default_models.default_speech_to_text_model,
    help="This is the default model for converting speech to text (audio transcriptions, etc)",
    model_type="speech_to_text",
    key="default_speech_to_text_model",
)

if selected_model:
    default_models.default_speech_to_text_model = selected_model.id

st.divider()
# Handle embedding model selection
selected_model = model_selector(
    "Default Embedding Model",
    "default_embedding_model",
    selected_id=default_models.default_embedding_model,
    help="This is the default model for embeddings (semantic search, etc)",
    model_type="embedding",
)
if selected_model:
    default_models.default_embedding_model = selected_model.id
st.warning(
    "Caution: you cannot change the embedding model once there is embeddings or they will need to be regenerated"
)

for k, v in defs.items():
    if v:
        defs[k] = v.id

if st.button("Save Defaults"):
    default_models.patch(defs)
    model_manager.refresh_defaults()
    st.success("Saved")
