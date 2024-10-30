import os

import streamlit as st

from open_notebook.domain.models import DefaultModels, Model
from open_notebook.models import MODEL_CLASS_MAP
from stream_app.utils import version_sidebar

st.set_page_config(
    layout="wide", page_title="⚙️ Settings", initial_sidebar_state="expanded"
)
version_sidebar()


st.title("Settings")

model_tab, model_defaults_tab = st.tabs(["Models", "Model Defaults"])

provider_status = {}

model_types = [
    # "vision",
    "language",
    "embedding",
    "text_to_speech",
    "speech_to_text",
]

provider_status["ollama"] = os.environ.get("OLLAMA_API_BASE") is not None
provider_status["openai"] = os.environ.get("OPENAI_API_KEY") is not None
provider_status["vertexai"] = (
    os.environ.get("VERTEX_PROJECT") is not None
    and os.environ.get("VERTEX_LOCATION") is not None
    and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
)
provider_status["vertexai-anthropic"] = (
    os.environ.get("VERTEX_PROJECT") is not None
    and os.environ.get("VERTEX_LOCATION") is not None
    and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
)
provider_status["gemini"] = os.environ.get("GEMINI_API_KEY") is not None
provider_status["openrouter"] = (
    os.environ.get("OPENROUTER_API_KEY") is not None
    and os.environ.get("OPENAI_API_KEY") is not None
    and os.environ.get("OPENROUTER_BASE_URL") is not None
)
provider_status["anthropic"] = os.environ.get("ANTHROPIC_API_KEY") is not None
provider_status["elevenlabs"] = os.environ.get("ELEVENLABS_API_KEY") is not None
provider_status["litellm"] = (
    provider_status["ollama"]
    or provider_status["vertexai"]
    or provider_status["vertexai-anthropic"]
    or provider_status["anthropic"]
    or provider_status["openai"]
    or provider_status["gemini"]
)

available_providers = [k for k, v in provider_status.items() if v]
unavailable_providers = [k for k, v in provider_status.items() if not v]

with model_tab:
    st.subheader("Add Model")
    provider = st.selectbox("Provider", available_providers)
    if len(unavailable_providers) > 0:
        st.caption(
            f"Unavailable Providers: {', '.join(unavailable_providers)}. Please check docs page if you wish to enable them."
        )

    # Filter model types based on provider availability in MODEL_CLASS_MAP
    available_model_types = []
    for model_type in model_types:
        if model_type in MODEL_CLASS_MAP and provider in MODEL_CLASS_MAP[model_type]:
            available_model_types.append(model_type)

    if not available_model_types:
        st.error(f"No compatible model types available for provider: {provider}")
    else:
        model_type = st.selectbox(
            "Model Type",
            available_model_types,
            help="Use language for text generation models, text_to_speech for TTS models for generating podcasts, etc.",
        )
        model_name = st.text_input(
            "Model Name", "", help="gpt-4o-mini, claude, gemini, llama3, etc"
        )
        if st.button("Save"):
            model = Model(name=model_name, provider=provider, type=model_type)
            model.save()
            st.success("Saved")
    st.divider()
    all_models = Model.get_all()
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


def get_selected_index(models, model_id, default=0):
    """Returns the index of the selected model in the list of models"""
    if not model_id or not models:
        return default
    for i, model in enumerate(models):
        if model.id == model_id:
            return i
    return default


with model_defaults_tab:
    default_models = DefaultModels.load().model_dump()
    all_models = Model.get_all()
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
    defs["default_chat_model"] = st.selectbox(
        "Default Chat Model",
        text_generation_models,
        format_func=lambda x: x.name,
        help="This model will be used for chat.",
        index=get_selected_index(
            text_generation_models, default_models.get("default_chat_model")
        ),
    )
    st.divider()
    defs["default_transformation_model"] = st.selectbox(
        "Default Transformation Model",
        text_generation_models,
        format_func=lambda x: x.name,
        help="This model will be used for text transformations such as summaries, insights, etc.",
        index=get_selected_index(
            text_generation_models, default_models.get("default_transformation_model")
        ),
    )
    st.caption("You can override this model on individual transformations")
    st.divider()
    defs["large_context_model"] = st.selectbox(
        "Large Context Model",
        text_generation_models,
        format_func=lambda x: x.name,
        help="This model will be used for larger context generation -- recommended: Gemini",
        index=get_selected_index(
            text_generation_models, default_models.get("large_context_model")
        ),
    )
    st.caption("Recommended to use Gemini models for larger context processing")
    st.divider()
    defs["default_text_to_speech_model"] = st.selectbox(
        "Default Text to Speech Model",
        text_to_speech_models,
        format_func=lambda x: x.name,
        help="This is the default model for converting text to speech (podcasts, etc)",
        index=get_selected_index(
            text_to_speech_models, default_models.get("default_text_to_speech_model")
        ),
    )
    st.caption("You can override this model on different podcasts")
    st.divider()
    defs["default_speech_to_text_model"] = st.selectbox(
        "Default Speech to Text Model",
        speech_to_text_models,
        format_func=lambda x: x.name,
        help="This is the default model for converting speech to text (audio transcriptions, etc)",
        index=get_selected_index(
            speech_to_text_models, default_models.get("default_speech_to_text_model")
        ),
    )
    st.divider()
    # defs["default_vision_model"] = st.selectbox(
    #     "Default Vision Model",
    #     vision_models,
    #     format_func=lambda x: x.name,
    #     help="This is the default model for vision tasks (image recognition, PDF recognition, etc)",
    #     index=get_selected_index(
    #         vision_models, default_models.get("default_vision_model")
    #     ),
    # )
    # st.divider()

    defs["default_embedding_model"] = st.selectbox(
        "Default Embedding Model",
        embedding_models,
        format_func=lambda x: x.name,
        help="This is the default model for embeddings (semantic search, etc)",
        index=get_selected_index(
            embedding_models, default_models.get("default_embedding_model")
        ),
    )
    st.caption(
        "Caution: you cannot change the embedding model once there is embeddings or they will need to be regenerated"
    )

    # if st.button("Save Defaults", key="save_defaults"):
    for k, v in defs.items():
        if v:
            defs[k] = v.id
    DefaultModels.update(defs)
