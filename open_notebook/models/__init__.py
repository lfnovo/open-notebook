from typing import Dict, Optional, Union

from open_notebook.domain.models import DefaultModels, Model
from open_notebook.models.embedding_models import (
    EmbeddingModel,
    GeminiEmbeddingModel,
    OllamaEmbeddingModel,
    OpenAIEmbeddingModel,
    VertexEmbeddingModel,
)
from open_notebook.models.llms import (
    AnthropicLanguageModel,
    GeminiLanguageModel,
    LanguageModel,
    LiteLLMLanguageModel,
    OllamaLanguageModel,
    OpenAILanguageModel,
    OpenRouterLanguageModel,
    VertexAILanguageModel,
    VertexAnthropicLanguageModel,
)
from open_notebook.models.speech_to_text_models import (
    OpenAISpeechToTextModel,
    SpeechToTextModel,
)
from open_notebook.models.text_to_speech_models import (
    ElevenLabsTextToSpeechModel,
    OpenAITextToSpeechModel,
    TextToSpeechModel,
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


class ModelManager:
    _instance = None
    _model_cache: Dict[str, object] = {}
    _default_models: Optional[DefaultModels] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.refresh_defaults()

    def refresh_defaults(self):
        """Refresh the default models from the database"""
        self._default_models = DefaultModels.load()

    @property
    def defaults(self) -> DefaultModels:
        """Get the default models configuration"""
        if not self._default_models:
            self.refresh_defaults()
        return self._default_models

    def get_model(
        self, model_id: str, **kwargs
    ) -> Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]:
        """
        Get a model instance based on model_id. Uses caching to avoid recreating instances.

        Args:
            model_id: The ID of the model to retrieve
            **kwargs: Additional arguments to pass to the model constructor
        """
        cache_key = f"{model_id}:{str(kwargs)}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

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
            model_instance = model_instance

        self._model_cache[cache_key] = model_instance
        return model_instance

    def get_default_model(
        self, model_type: str, **kwargs
    ) -> Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]:
        """
        Get the default model for a specific type.

        Args:
            model_type: The type of model to retrieve (e.g., 'chat', 'embedding', etc.)
            **kwargs: Additional arguments to pass to the model constructor
        """
        model_id = None

        if model_type == "chat":
            model_id = self.defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                self.defaults.default_transformation_model
                or self.defaults.default_chat_model
            )
        elif model_type == "embedding":
            model_id = self.defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = self.defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = self.defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = self.defaults.large_context_model

        if not model_id:
            raise ValueError(f"No default model configured for type: {model_type}")

        return self.get_model(model_id, **kwargs)

    def clear_cache(self):
        """Clear the model cache"""
        self._model_cache.clear()


model_manager = ModelManager()
