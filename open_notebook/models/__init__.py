from typing import Dict, Type, Union

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
    XAILanguageModel,
)
from open_notebook.models.speech_to_text_models import (
    OpenAISpeechToTextModel,
    SpeechToTextModel,
)
from open_notebook.models.text_to_speech_models import (
    ElevenLabsTextToSpeechModel,
    GeminiTextToSpeechModel,
    OpenAITextToSpeechModel,
    TextToSpeechModel,
)

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]


ProviderMap = Dict[str, Type[ModelType]]

MODEL_CLASS_MAP: Dict[str, ProviderMap] = {
    "language": {
        "ollama": OllamaLanguageModel,
        "openrouter": OpenRouterLanguageModel,
        "vertexai-anthropic": VertexAnthropicLanguageModel,
        "litellm": LiteLLMLanguageModel,
        "vertexai": VertexAILanguageModel,
        "anthropic": AnthropicLanguageModel,
        "openai": OpenAILanguageModel,
        "gemini": GeminiLanguageModel,
        "xai": XAILanguageModel,
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
        "gemini": GeminiTextToSpeechModel,
    },
}

__all__ = [
    "MODEL_CLASS_MAP",
    "EmbeddingModel",
    "LanguageModel",
    "SpeechToTextModel",
    "TextToSpeechModel",
    "ModelType",
]
