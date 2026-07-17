from typing import Any

from esperanto import LanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger

from open_notebook.ai.models import model_manager
from open_notebook.exceptions import ConfigurationError
from open_notebook.utils import token_count


def _to_langchain(model: LanguageModel) -> BaseChatModel:
    """Convert a model while preserving Anthropic-compatible base URLs.

    Esperanto's to_langchain() maps anthropic_compatible to the Anthropic
    implementation but drops the custom base_url; re-inject it via ChatAnthropic.
    """
    if getattr(model, "_open_notebook_provider", None) != "anthropic_compatible":
        return model.to_langchain()

    from langchain_anthropic import ChatAnthropic

    base_url = model.base_url.rstrip("/") if model.base_url else None
    if base_url and base_url.endswith("/v1"):
        base_url = base_url.removesuffix("/v1")

    config: dict[str, Any] = {
        "model": model.get_model_name(),
        "max_tokens": model.max_tokens,
        "api_key": model.api_key,
        "base_url": base_url,
    }
    if model.temperature is not None:
        config["temperature"] = model.temperature
    elif model.top_p is not None:
        config["top_p"] = model.top_p
    return ChatAnthropic(**config)


async def provision_langchain_model(
    content, model_id, default_type, **kwargs
) -> BaseChatModel:
    """
    Returns the best model to use based on the context size and on whether there is a specific model being requested in Config.
    If context > 105_000, returns the large_context_model
    If model_id is specified in Config, returns that model
    Otherwise, returns the default model for the given type
    """
    tokens = token_count(content)
    model = None
    selection_reason = ""

    if tokens > 105_000:
        selection_reason = f"large_context (content has {tokens} tokens)"
        logger.debug(
            f"Using large context model because the content has {tokens} tokens"
        )
        model = await model_manager.get_default_model("large_context", **kwargs)
    elif model_id:
        selection_reason = f"explicit model_id={model_id}"
        model = await model_manager.get_model(model_id, **kwargs)
    else:
        selection_reason = f"default for type={default_type}"
        model = await model_manager.get_default_model(default_type, **kwargs)

    logger.debug(f"Using model: {model}")

    if model is None:
        logger.error(
            f"Model provisioning failed: No model found. "
            f"Selection reason: {selection_reason}. "
            f"model_id={model_id}, default_type={default_type}. "
            f"Please check Settings → Models and ensure a default model is configured for '{default_type}'."
        )
        raise ConfigurationError(
            f"No model configured for {selection_reason}. "
            f"Please go to Settings → Models and configure a default model for '{default_type}'."
        )

    if not isinstance(model, LanguageModel):
        logger.error(
            f"Model type mismatch: Expected LanguageModel but got {type(model).__name__}. "
            f"Selection reason: {selection_reason}. "
            f"model_id={model_id}, default_type={default_type}."
        )
        raise ConfigurationError(
            f"Model is not a LanguageModel: {model}. "
            f"Please check that the model configured for '{default_type}' is a language model, not an embedding or speech model."
        )

    return _to_langchain(model)
