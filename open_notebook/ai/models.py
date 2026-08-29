import os
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Union

from esperanto import (
    AIFactory,
    EmbeddingModel,
    LanguageModel,
    SpeechToTextModel,
    TextToSpeechModel,
)
from loguru import logger
from surrealdb import RecordID

from open_notebook.ai.connection_tester import normalize_anthropic_compatible_base_url
from open_notebook.ai.pricing import get_price_per_token
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.exceptions import ConfigurationError
from open_notebook.utils.url_validation import validate_url

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]

# Config keys from Credential.to_esperanto_config() that may carry a
# user-configured URL (ollama/azure/openai_compatible/vertex).
_URL_CONFIG_KEYS = (
    "base_url",
    "endpoint",
    "endpoint_llm",
    "endpoint_embedding",
    "endpoint_stt",
    "endpoint_tts",
)


async def _revalidate_config_urls(config: dict, provider: str) -> None:
    """
    Re-validate a credential's URL fields immediately before they're used for
    a real request.

    validate_url() is also enforced when a credential is created/updated, but
    that alone leaves a DNS-rebinding TOCTOU window: a hostname that resolved
    to a public IP at save time can later be repointed to an internal/
    metadata address, and Esperanto/httpx re-resolve DNS fresh on every
    connection. Re-checking here narrows that window to "this call", instead
    of "any time after the credential was saved".
    """
    for key in _URL_CONFIG_KEYS:
        value = config.get(key)
        if value:
            try:
                await validate_url(value, provider)
            except ValueError as e:
                raise ConfigurationError(str(e)) from e


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    nullable_fields: ClassVar[set[str]] = {"credential"}
    name: str
    provider: str
    type: str
    credential: Optional[str] = None

    @classmethod
    async def get_models_by_type(cls, model_type):
        models = await repo_query(
            "SELECT * FROM model WHERE type=$model_type;", {"model_type": model_type}
        )
        return [Model(**model) for model in models]

    @classmethod
    async def get_display_info_for_ids(
        cls, model_ids: Sequence[Union[str, RecordID]]
    ) -> Dict[str, Dict[str, str]]:
        """
        Batch-fetch {provider, name} display info for many model IDs in one
        query.

        Episode listing resolves the model references stored in the
        denormalized episode/speaker profile snapshots (outline_llm,
        transcript_llm, voice_model) into human-readable display fields.
        Doing that with Model.get() would cost one round trip per reference
        per episode (no connection pooling in the repository layer) - this
        collects the distinct IDs and resolves them in a single query,
        mirroring PodcastEpisode.get_job_details_for_commands().

        Unresolvable IDs (deleted models) are simply absent from the result;
        a total query failure returns an empty dict so display resolution
        degrades gracefully instead of breaking the caller.
        """
        ids = sorted({str(mid) for mid in model_ids if mid})
        grouped: Dict[str, Dict[str, str]] = {}
        if not ids:
            return grouped
        try:
            result = await repo_query(
                "SELECT id, name, provider FROM model WHERE id IN $model_ids",
                {"model_ids": [ensure_record_id(mid) for mid in ids]},
            )
        except Exception as e:
            logger.error(f"Error batch-fetching model display info: {e}")
            return grouped
        for row in result:
            grouped[str(row.get("id"))] = {
                "provider": row.get("provider", ""),
                "name": row.get("name", ""),
            }
        return grouped

    @classmethod
    async def get_by_credential(cls, credential_id: str):
        """Get all models linked to a specific credential."""
        models = await repo_query(
            "SELECT * FROM model WHERE credential=$cred_id;",
            {"cred_id": ensure_record_id(credential_id)},
        )
        return [Model(**model) for model in models]

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        if data.get("credential"):
            data["credential"] = ensure_record_id(data["credential"])
        return data

    async def get_credential_obj(self):
        """Get the Credential object linked to this model, if any."""
        if not self.credential:
            return None
        from open_notebook.domain.credential import Credential

        try:
            return await Credential.get(self.credential)
        except Exception:
            logger.warning(f"Could not load credential {self.credential} for model {self.id}")
            return None


class DefaultModels(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_models"
    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    # default_vision_model: Optional[str]
    default_embedding_model: Optional[str] = None
    default_tools_model: Optional[str] = None

    # Ordered fallback chains, one per task type. The default_*_model /
    # large_context_model fields above stay the primary/first entry for full
    # backward compatibility - these are purely additive and default to an
    # empty list, so a config with no fallbacks configured (the vast
    # majority, both local and production) behaves exactly as before. See
    # ModelManager.get_fallback_chain() and
    # open_notebook.ai.provision.provision_langchain_model() for how these
    # are resolved and wired into LangChain's Runnable.with_fallbacks().
    chat_fallback_models: List[str] = []
    transformation_fallback_models: List[str] = []
    large_context_fallback_models: List[str] = []
    tools_fallback_models: List[str] = []
    embedding_fallback_models: List[str] = []
    text_to_speech_fallback_models: List[str] = []
    speech_to_text_fallback_models: List[str] = []

    @classmethod
    async def get_instance(cls) -> "DefaultModels":
        """Always fetch fresh defaults from database (override parent caching behavior)"""
        result = await repo_query(
            "SELECT * FROM ONLY $record_id",
            {"record_id": ensure_record_id(cls.record_id)},
        )

        if result:
            if isinstance(result, list) and len(result) > 0:
                data = result[0]
            elif isinstance(result, dict):
                data = result
            else:
                data = {}
        else:
            data = {}

        # Create new instance with fresh data (bypass singleton cache)
        instance = object.__new__(cls)
        object.__setattr__(instance, "__dict__", {})
        super(RecordModel, instance).__init__(**data)
        return instance


# Maps a provision_langchain_model()/get_default_model() `model_type` (also
# used as the usage-tracking `task_type`) to the DefaultModels field holding
# its ordered fallback chain. Only types that actually go through
# provision_langchain_model() (language models) currently get real fallback
# *behavior* wired up (see provision.py); embedding/tts/stt entries are
# still resolved here for API/Settings-UI completeness even though nothing
# consumes them yet.
_FALLBACK_FIELD_BY_TYPE = {
    "chat": "chat_fallback_models",
    "transformation": "transformation_fallback_models",
    "tools": "tools_fallback_models",
    "large_context": "large_context_fallback_models",
    "embedding": "embedding_fallback_models",
    "text_to_speech": "text_to_speech_fallback_models",
    "speech_to_text": "speech_to_text_fallback_models",
}


def _provider_and_name(model: "ModelType") -> tuple[Optional[str], Optional[str]]:
    """(provider, model_name) for any Esperanto model type.

    Esperanto's TextToSpeechModel is the one type without `.provider` /
    `.get_model_name()` (it only exposes `.model_name`, no provider
    attribute at all) - everything else (LanguageModel, EmbeddingModel,
    SpeechToTextModel) has both. Centralized here so fallback-chain
    resolution works uniformly across task types without hitting an
    AttributeError on TTS.
    """
    provider = getattr(model, "provider", None)
    if hasattr(model, "get_model_name"):
        model_name = model.get_model_name()
    else:
        model_name = getattr(model, "model_name", None)
    return provider, model_name


class ModelManager:
    def __init__(self):
        pass  # No caching needed

    async def get_model(self, model_id: str, **kwargs) -> Optional[ModelType]:
        """Get a model by ID. Esperanto will cache the actual model instance."""
        if not model_id:
            return None

        try:
            model: Model = await Model.get(model_id)
        except Exception:
            raise ConfigurationError(f"Model with ID {model_id} not found")

        if not model.type or model.type not in [
            "language",
            "embedding",
            "speech_to_text",
            "text_to_speech",
        ]:
            raise ConfigurationError(f"Invalid model type: {model.type}")

        # Build config from credential if linked, otherwise fall back to env vars
        config: dict = {}
        if model.credential:
            credential = await model.get_credential_obj()
            if credential:
                config = credential.to_esperanto_config()
                await _revalidate_config_urls(config, model.provider)
                logger.debug(
                    f"Using credential '{credential.name}' for model {model.name}"
                )
            else:
                logger.warning(
                    f"Model {model.id} has credential {model.credential} but it could not be loaded. "
                    f"Falling back to env vars."
                )
                # Fall back to env var provisioning
                from open_notebook.ai.key_provider import provision_provider_keys

                await provision_provider_keys(model.provider)
        else:
            # No credential linked - use env var fallback
            from open_notebook.ai.key_provider import provision_provider_keys

            await provision_provider_keys(model.provider)

        # anthropic_compatible: esperanto has no such provider name; it maps to
        # the anthropic provider with a custom base_url. Pull config from env when
        # no credential is linked. This runs BEFORE kwargs are merged so that a
        # kwarg like temperature does not make `config` truthy and suppress the
        # env-var fallback for an unlinked model.
        if model.provider == "anthropic_compatible" and not config:
            api_key = os.environ.get("ANTHROPIC_COMPATIBLE_API_KEY")
            base_url = os.environ.get("ANTHROPIC_COMPATIBLE_BASE_URL")
            if api_key:
                config["api_key"] = api_key
            if base_url:
                config["base_url"] = base_url
                # A base_url from a provisioned DB credential needs the same
                # request-time re-validation the credential-linked path gets.
                await _revalidate_config_urls(config, model.provider)

        # Merge any additional kwargs (e.g. temperature)
        config.update(kwargs)

        # Require base_url + api_key and normalize the URL for anthropic_compatible.
        if model.provider == "anthropic_compatible" and (
            not str(config.get("api_key", "")).strip()
            or not str(config.get("base_url", "")).strip()
        ):
            raise ConfigurationError(
                "Anthropic-compatible models require a base URL and API key"
            )
        if model.provider == "anthropic_compatible":
            config["base_url"] = normalize_anthropic_compatible_base_url(
                str(config["base_url"])
            )

        # Normalize provider name: DB stores underscores but Esperanto expects hyphens
        provider = (
            "anthropic"
            if model.provider == "anthropic_compatible"
            else model.provider.replace("_", "-")
        )

        # Create model based on type (Esperanto will cache the instance)
        if model.type == "language":
            return AIFactory.create_language(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "embedding":
            return AIFactory.create_embedding(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "speech_to_text":
            return AIFactory.create_speech_to_text(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "text_to_speech":
            return AIFactory.create_text_to_speech(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        else:
            raise ConfigurationError(f"Invalid model type: {model.type}")

    async def get_defaults(self) -> DefaultModels:
        """Get the default models configuration from database"""
        defaults = await DefaultModels.get_instance()
        if not defaults:
            raise RuntimeError("Failed to load default models configuration")
        return defaults

    async def get_speech_to_text(self, **kwargs) -> Optional[SpeechToTextModel]:
        """Get the default speech-to-text model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_speech_to_text_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, SpeechToTextModel), (
            f"Expected SpeechToTextModel but got {type(model)}"
        )
        return model

    async def get_text_to_speech(self, **kwargs) -> Optional[TextToSpeechModel]:
        """Get the default text-to-speech model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_text_to_speech_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, TextToSpeechModel), (
            f"Expected TextToSpeechModel but got {type(model)}"
        )
        return model

    async def get_embedding_model(self, **kwargs) -> Optional[EmbeddingModel]:
        """Get the default embedding model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, EmbeddingModel), (
            f"Expected EmbeddingModel but got {type(model)}"
        )
        return model

    async def get_default_model(self, model_type: str, **kwargs) -> Optional[ModelType]:
        """
        Get the default model for a specific type.

        Args:
            model_type: The type of model to retrieve (e.g., 'chat', 'embedding', etc.)
            **kwargs: Additional arguments to pass to the model constructor
        """
        defaults = await self.get_defaults()
        model_id = None

        if model_type == "chat":
            model_id = defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                defaults.default_transformation_model or defaults.default_chat_model
            )
        elif model_type == "tools":
            model_id = defaults.default_tools_model or defaults.default_chat_model
        elif model_type == "embedding":
            model_id = defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = defaults.large_context_model or defaults.default_chat_model

        if not model_id:
            logger.warning(
                f"No default model configured for type '{model_type}'. "
                f"Please go to Settings → Models and set a default model."
            )
            return None

        try:
            return await self.get_model(model_id, **kwargs)
        except (ValueError, ConfigurationError) as e:
            logger.error(
                f"Failed to load default model for type '{model_type}': {e}. "
                f"The configured model_id '{model_id}' may have been deleted or misconfigured. "
                f"Please go to Settings → Models and reconfigure the default model."
            )
            return None

    async def get_fallback_chain(
        self,
        model_type: str,
        primary_provider: Optional[str] = None,
        primary_model_name: Optional[str] = None,
        **kwargs,
    ) -> List[ModelType]:
        """Resolve the ordered fallback chain configured for a task type.

        Returns already-instantiated Esperanto model objects (same shape as
        get_model()/get_default_model()), ready for the caller to convert to
        LangChain form and combine with the primary via with_fallbacks().

        Skips, without breaking the rest of the chain:
        - a fallback entry that resolves to the same (provider, model_name)
          as the primary (never fall back to the model that just failed;
          compared by provider+name rather than DB id since the caller only
          has the already-instantiated Esperanto primary model in hand, not
          its record id)
        - any id that fails to resolve (deleted model, missing/broken
          credential) - logged at WARNING and skipped
        - paid models (non-zero OpenRouter pricing) once trailing spend is at
          or over the configured budget (STUDY_BUDGET_USD). Free ($0) models
          are never excluded by budget. The budget check runs at most once
          per call (lazily, only once a paid candidate is actually seen).
        """
        field_name = _FALLBACK_FIELD_BY_TYPE.get(model_type)
        if not field_name:
            return []

        defaults = await self.get_defaults()
        fallback_ids = getattr(defaults, field_name, None) or []
        if not fallback_ids:
            return []

        resolved: List[ModelType] = []
        budget_ok: Optional[bool] = None

        for fallback_id in fallback_ids:
            if not fallback_id:
                continue

            try:
                fb_model = await self.get_model(fallback_id, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Skipping fallback model {fallback_id} for '{model_type}': "
                    f"could not resolve it ({e})"
                )
                continue

            if fb_model is None:
                continue

            fb_provider, fb_model_name = _provider_and_name(fb_model)

            if (
                primary_provider is not None
                and primary_model_name is not None
                and fb_provider == primary_provider
                and fb_model_name == primary_model_name
            ):
                continue

            input_price, output_price = await get_price_per_token(
                fb_provider or "", fb_model_name or ""
            )
            is_paid = input_price > 0 or output_price > 0

            if is_paid:
                if budget_ok is None:
                    from open_notebook.domain.usage import UsageEvent

                    budget_ok = await UsageEvent.is_within_budget()
                if not budget_ok:
                    logger.info(
                        f"Skipping paid fallback model {fallback_id} for "
                        f"'{model_type}': STUDY_BUDGET_USD exhausted"
                    )
                    continue

            resolved.append(fb_model)

        return resolved


model_manager = ModelManager()
