from open_notebook.domain.models import Model
from open_notebook.models.embedding_models import OpenAIEmbeddingModel
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
    },
    "speech_to_text": {
        "openai": OpenAISpeechToTextModel,
    },
}


def get_model(model_id, model_type="language", **kwargs):
    """
    Get a model instance based on model_id and type.

    Args:
        model_id: The ID of the model to retrieve
        model_type: Type of model ('language', 'embedding', or 'speech_to_text')
        **kwargs: Additional arguments to pass to the model constructor
    """
    assert model_id, "Model ID cannot be empty"
    model: Model = Model.get(model_id)

    if not model:
        raise ValueError(f"Model with ID {model_id} not found")

    if model_type not in MODEL_CLASS_MAP:
        raise ValueError(f"Invalid model type: {model_type}")

    provider_map = MODEL_CLASS_MAP[model_type]
    if model.provider not in provider_map:
        raise ValueError(
            f"Provider {model.provider} not compatible with {model_type} models"
        )

    model_class = provider_map[model.provider]
    model_instance = model_class(model_name=model.name, **kwargs)

    # Special handling for language models that need langchain conversion
    if model_type == "language":
        return model_instance.to_langchain()

    return model_instance
