from open_notebook.domain.models import Model
from open_notebook.models.embedding_models import (
    GeminiEmbeddingModel,
    OllamaEmbeddingModel,
    OpenAIEmbeddingModel,
    VertexEmbeddingModel,
)
from open_notebook.models.llms import (
    AnthropicLanguageModel,
    GeminiLanguageModel,
    LiteLLMLanguageModel,
    OllamaLanguageModel,
    OpenAILanguageModel,
    OpenRouterLanguageModel,
    VertexAILanguageModel,
    VertexAnthropicLanguageModel,
)
from open_notebook.models.speech_to_text_models import OpenAISpeechToTextModel
from open_notebook.models.text_to_speech_models import (
    ElevenLabsTextToSpeechModel,
    OpenAITextToSpeechModel,
)

# Unified model class map with type information
MODEL_CLASS_MAP = {
    "language": {
        "ollama": OllamaLanguageModel,
        "openrouter": OpenRouterLanguageModel,
        "vertexai-anthropic": VertexAnthropicLanguageModel,
        "litellm": LiteLLMLanguageModel,
        "vertexai": VertexAILanguageModel,
        "anthropic": AnthropicLanguageModel,
        "openai": OpenAILanguageModel,
        "gemini": GeminiLanguageModel,
    },
    "embedding": {
        "openai": OpenAIEmbeddingModel,
        "gemini": GeminiEmbeddingModel,
        "vertexai": VertexEmbeddingModel,
        "ollama": OllamaEmbeddingModel,
    },
    "speech_to_text": {
        "openai": OpenAISpeechToTextModel,
    },
    "text_to_speech": {
        "openai": OpenAITextToSpeechModel,
        "elevenlabs": ElevenLabsTextToSpeechModel,
    },
}


def get_model(model_id, **kwargs):
    """
    Get a model instance based on model_id and type.

    Args:
        model_id: The ID of the model to retrieve
        **kwargs: Additional arguments to pass to the model constructor
    """
    assert model_id, "Model ID cannot be empty"
    model: Model = Model.get(model_id)

    if not model:
        raise ValueError(f"Model with ID {model_id} not found")

    if not model.type or model.type not in MODEL_CLASS_MAP:
        raise ValueError(f"Invalid model type: {model.type}")

    provider_map = MODEL_CLASS_MAP[model.type]
    if model.provider not in provider_map:
        raise ValueError(
            f"Provider {model.provider} not compatible with {model.type} models"
        )

    model_class = provider_map[model.provider]
    model_instance = model_class(model_name=model.name, **kwargs)

    # Special handling for language models that need langchain conversion
    if model.type == "language":
        return model_instance.to_langchain()

    return model_instance
