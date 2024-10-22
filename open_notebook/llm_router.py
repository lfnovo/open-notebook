from open_notebook.llms import (
    AnthropicLanguageModel,
    LiteLLMLanguageModel,
    OllamaLanguageModel,
    OpenAILanguageModel,
    OpenRouterLanguageModel,
    VertexAILanguageModel,
    VertexAnthropicLanguageModel,
)

# Map provider names to classes
PROVIDER_CLASS_MAP = {
    "ollama": OllamaLanguageModel,
    "openrouter": OpenRouterLanguageModel,
    "vertexai-anthropic": VertexAnthropicLanguageModel,
    "litellm": LiteLLMLanguageModel,
    "vertexai": VertexAILanguageModel,
    "anthropic": AnthropicLanguageModel,
    "openai": OpenAILanguageModel,
}


def get_langchain_model(model_name, json=False):
    parts = model_name.split("/")
    provider = parts[0]
    model_name_wihout_provider = "/".join(parts[1:])
    if provider not in PROVIDER_CLASS_MAP.keys():
        raise ValueError(
            f"Provider {provider} not found in config. Make sure you use the correct format for model names, example: openai/gpt-4o-mini"
        )
    return PROVIDER_CLASS_MAP[provider](
        model_name=model_name_wihout_provider, json=json
    ).to_langchain()
