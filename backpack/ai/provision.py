from esperanto import LanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger

from backpack.ai.models import model_manager
from backpack.utils import token_count

# Keep references to prevent GC from closing the shared httpx client
_esperanto_model_refs: list = []


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

    if tokens > 105_000:
        logger.debug(
            f"Using large context model because the content has {tokens} tokens"
        )
        model = await model_manager.get_default_model("large_context", **kwargs)
    elif model_id:
        model = await model_manager.get_model(model_id, **kwargs)
    else:
        model = await model_manager.get_default_model(default_type, **kwargs)

    logger.debug(f"Using model: {model}")
    assert isinstance(model, LanguageModel), f"Model is not a LanguageModel: {model}"

    # Keep a reference to prevent GC from closing the shared httpx client
    if len(_esperanto_model_refs) > 100:
        _esperanto_model_refs.clear()  # Prevent unbounded memory growth
    _esperanto_model_refs.append(model)

    return model.to_langchain()
