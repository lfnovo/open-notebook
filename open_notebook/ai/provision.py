from typing import Any, List, Tuple

from esperanto import LanguageModel
from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import LLMResult
from langchain_core.runnables import Runnable
from loguru import logger

from open_notebook.ai.models import ModelType, model_manager
from open_notebook.ai.pricing import get_price_per_token
from open_notebook.exceptions import ConfigurationError
from open_notebook.utils import token_count


def _extract_token_usage(response: LLMResult) -> Tuple[int, int]:
    """Pull (input_tokens, output_tokens) out of an LLMResult, provider-agnostic.

    Different LangChain chat model integrations report usage in different
    places: `llm_output["token_usage"]` (OpenAI-style: prompt_tokens/
    completion_tokens), `llm_output["usage"]` (Anthropic-style: input_tokens/
    output_tokens), or - on newer integrations - per-message
    `usage_metadata` on the generated AIMessage. Try each; default to (0, 0)
    when none are present (some providers don't report usage at all).
    """
    llm_output = response.llm_output or {}
    token_usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
    input_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
    output_tokens = (
        token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
    )

    if not input_tokens and not output_tokens:
        try:
            for generations in response.generations:
                for generation in generations:
                    message = getattr(generation, "message", None)
                    usage_metadata = (
                        getattr(message, "usage_metadata", None) if message else None
                    )
                    if usage_metadata:
                        input_tokens = usage_metadata.get("input_tokens", 0)
                        output_tokens = usage_metadata.get("output_tokens", 0)
                        break
                if input_tokens or output_tokens:
                    break
        except Exception:
            pass

    return int(input_tokens or 0), int(output_tokens or 0)


class UsageTrackingCallbackHandler(AsyncCallbackHandler):
    """Records a `UsageEvent` for every completed LLM call.

    Bound onto the LangChain model instance returned by
    `provision_langchain_model()` (via its `callbacks` field) so every graph/
    command that goes through that single choke point gets usage tracking
    for free, with no per-call-site changes. A logging failure here must
    never break the actual LLM call, so everything is wrapped and only
    logged at WARNING.
    """

    def __init__(self, provider: str, model_name: str, task_type: str) -> None:
        self.provider = provider
        self.model_name = model_name
        self.task_type = task_type

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            input_tokens, output_tokens = _extract_token_usage(response)
            if not input_tokens and not output_tokens:
                return

            input_price, output_price = await get_price_per_token(
                self.provider, self.model_name
            )
            estimated_cost_usd = (
                input_tokens * input_price + output_tokens * output_price
            )

            # Imported lazily to avoid a module-load-time dependency from
            # open_notebook.ai (imported very early, e.g. by the worker) on
            # the domain/database layers.
            from open_notebook.domain.usage import UsageEvent

            event = UsageEvent(
                provider=self.provider,
                model_name=self.model_name,
                task_type=self.task_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=estimated_cost_usd,
            )
            await event.save()
        except Exception as e:
            logger.warning(f"Failed to record LLM usage event: {e}")


def _attach_usage_tracking(
    lc_model: BaseChatModel, provider: str, model_name: str, task_type: str
) -> BaseChatModel:
    """Best-effort: bind a usage-tracking callback onto the model instance.

    Never raises - a failure here must not prevent the model from being
    returned and used.
    """
    try:
        handler = UsageTrackingCallbackHandler(provider, model_name, task_type)
        existing_callbacks = lc_model.callbacks
        existing: list = (
            list(existing_callbacks)
            if isinstance(existing_callbacks, list)
            else list(existing_callbacks.handlers)
            if existing_callbacks is not None
            else []
        )
        lc_model.callbacks = [*existing, handler]
    except Exception as e:
        logger.warning(f"Failed to attach usage tracking callback: {e}")
    return lc_model


async def provision_langchain_model(
    content, model_id, default_type, **kwargs
) -> Runnable:
    """
    Returns the best model to use based on the context size and on whether there is a specific model being requested in Config.
    If context > 105_000, returns the large_context_model
    If model_id is specified in Config, returns that model
    Otherwise, returns the default model for the given type

    When the resolved task type (large_context, or default_type otherwise)
    has a fallback chain configured in Settings -> Models, the returned
    Runnable is `primary.with_fallbacks(fallbacks)` (LangChain's native
    failover primitive: on invocation error it retries with the next model
    in the list, in order) instead of the bare primary model. With no
    fallbacks configured - true for the large majority of existing
    single-default-model setups - this returns exactly what it always did:
    the bare primary BaseChatModel, unchanged behavior.
    """
    tokens = token_count(content)
    model = None
    selection_reason = ""
    fallback_type = default_type

    if tokens > 105_000:
        selection_reason = f"large_context (content has {tokens} tokens)"
        logger.debug(
            f"Using large context model because the content has {tokens} tokens"
        )
        fallback_type = "large_context"
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

    provider = model.provider
    model_name = model.get_model_name()

    lc_model = model.to_langchain()
    lc_model = _attach_usage_tracking(lc_model, provider, model_name, default_type)

    # Resolve the configured fallback chain for the resolved task type
    # (large_context when the content was big enough to auto-upgrade,
    # otherwise the default_type the caller asked for). Any failure here is
    # logged and treated as "no fallbacks configured" - a broken fallback
    # chain must never prevent the primary model from being returned.
    fallback_models: List[ModelType] = []
    try:
        fallback_models = await model_manager.get_fallback_chain(
            fallback_type,
            primary_provider=provider,
            primary_model_name=model_name,
            **kwargs,
        )
    except Exception as e:
        logger.warning(
            f"Failed to resolve fallback chain for '{fallback_type}': {e}. "
            f"Continuing with the primary model only."
        )

    if not fallback_models:
        return lc_model

    # Usage tracking is attached to each model in the chain individually,
    # BEFORE combining them with with_fallbacks(), rather than to the
    # combined RunnableWithFallbacks. with_fallbacks() tries the primary,
    # and on failure invokes the next runnable in order - whichever
    # runnable actually ends up serving the call fires its own bound
    # callbacks as part of its own invocation, so this attributes
    # cost/tokens to whichever model in the chain actually served the
    # request, not just the primary's identity.
    fallback_lc_models: List[BaseChatModel] = []
    for fb_model in fallback_models:
        if not isinstance(fb_model, LanguageModel):
            logger.warning(
                f"Skipping fallback for '{fallback_type}': "
                f"{type(fb_model).__name__} is not a LanguageModel."
            )
            continue
        fb_lc = fb_model.to_langchain()
        fb_lc = _attach_usage_tracking(
            fb_lc, fb_model.provider, fb_model.get_model_name(), default_type
        )
        fallback_lc_models.append(fb_lc)

    if not fallback_lc_models:
        return lc_model

    logger.debug(
        f"Wiring {len(fallback_lc_models)} fallback model(s) for '{fallback_type}' "
        f"behind primary {provider}/{model_name}"
    )
    return lc_model.with_fallbacks(fallback_lc_models)
