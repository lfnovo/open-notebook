import os

from esperanto import LanguageModel
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger

from open_notebook.ai.models import model_manager
from open_notebook.exceptions import ConfigurationError, RateLimitError
from open_notebook.utils import token_count


class _RateLimitRetryModel(BaseChatModel):
    """
    LangChain wrapper that retries on RateLimitError with a fallback API key.

    Wraps a LangChain model and swaps to the fallback OpenAI key when a
    rate limit is encountered during .invoke() or .ainvoke().
    """

    def __init__(self, primary_model: BaseChatModel, fallback_key: str):
        super().__init__()
        self.primary_model = primary_model
        self.fallback_key = fallback_key

    def _invoke_with_fallback(self, method, *args, **kwargs):
        """Try primary model first, retry with fallback on RateLimitError."""
        try:
            return method(*args, **kwargs)
        except RateLimitError:
            logger.warning(
                "Primary model hit rate limit. Retrying with OpenAI API key fallback."
            )
            # Swap in fallback key
            original_key = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = self.fallback_key
            try:
                # Re-provision and recreate model with fallback key
                # We need the model name and provider to recreate it
                # Since we only have the LangChain model, recreate via a fresh provision
                fallback_model = self._create_fallback_model()
                return method.__func__(fallback_model, *args, **kwargs)
            finally:
                if original_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_key
                else:
                    os.environ.pop("OPENAI_API_KEY", None)

    def _create_fallback_model(self) -> BaseChatModel:
        """Recreate the model using the fallback API key by re-provisioning."""
        # Get the underlying Esperanto model and re-create with fallback key
        # The primary_model is a LangChain wrapper around an Esperanto model
        # We access the underlying model via private attribute
        underlying = getattr(self.primary_model, "model", None)
        if underlying is None:
            # Fallback: just use primary model and let it fail
            return self.primary_model

        # Get model metadata from the underlying Esperanto model
        model_name = getattr(underlying, "model_name", None) or getattr(underlying, "name", None)
        provider = getattr(underlying, "provider", None)

        if not model_name or not provider:
            return self.primary_model

        # Provision the provider (this will set env vars from DB, then we override with fallback)
        import asyncio

        from open_notebook.ai.key_provider import provision_provider_keys
        asyncio.run(provision_provider_keys(provider.replace("-", "_")))

        # Override with fallback key
        os.environ["OPENAI_API_KEY"] = self.fallback_key

        # Recreate via AIFactory
        from esperanto import AIFactory

        provider_normalized = provider.replace("_", "-")
        new_model = AIFactory.create_language(
            model_name=model_name,
            provider=provider_normalized,
            config={},
        )
        return new_model.to_langchain()

    @property
    def _llm_type(self) -> str:
        return self.primary_model._llm_type if hasattr(self.primary_model, "_llm_type") else "rate_limit_retry"

    def _generate(self, *args, **kwargs):
        return self._invoke_with_fallback(self.primary_model._generate, *args, **kwargs)

    async def _agenerate(self, *args, **kwargs):
        return await self._invoke_with_fallback(self.primary_model._agenerate, *args, **kwargs)

    def invoke(self, *args, **kwargs):
        return self._invoke_with_fallback(self.primary_model.invoke, *args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        return await self._invoke_with_fallback(self.primary_model.ainvoke, *args, **kwargs)


async def provision_langchain_model(
    content, model_id, default_type, team_id=None, **kwargs
) -> BaseChatModel:
    """
    Returns the best model to use based on the context size and on whether there is a specific model being requested in Config.
    If context > 105_000, returns the large_context_model
    If model_id is specified in Config, returns that model
    Otherwise, returns the default model for the given type

    When the model hits a rate limit and OPENAI_API_KEY_FALLBACK is set,
    automatically retries with the fallback key.
    """
    fallback_key = os.environ.get("OPENAI_API_KEY_FALLBACK")
    tokens = token_count(content)
    model = None
    selection_reason = ""

    if tokens > 105_000:
        selection_reason = f"large_context (content has {tokens} tokens)"
        logger.debug(
            f"Using large context model because the content has {tokens} tokens"
        )
        model = await model_manager.get_default_model(
            "large_context", team_id=team_id, **kwargs
        )
    elif model_id:
        selection_reason = f"explicit model_id={model_id}"
        model = await model_manager.get_model(model_id, **kwargs)
    else:
        selection_reason = f"default for type={default_type}"
        model = await model_manager.get_default_model(
            default_type, team_id=team_id, **kwargs
        )

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

    langchain_model = model.to_langchain()

    # Wrap with rate-limit retry if fallback key is available
    if fallback_key:
        logger.debug("OPENAI_API_KEY_FALLBACK set — wrapping model with rate-limit retry")
        return _RateLimitRetryModel(langchain_model, fallback_key)

    return langchain_model
