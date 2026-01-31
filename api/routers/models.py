import os
from typing import Dict, List, Optional

from esperanto import AIFactory
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from api.models import (
    DefaultModelsResponse,
    ModelCreate,
    ModelResponse,
    ProviderAvailabilityResponse,
)
from open_notebook.ai.key_provider import get_api_key, get_provider_config
from open_notebook.ai.model_discovery import (
    discover_provider_models,
    get_provider_model_count,
    sync_all_providers,
    sync_provider_models,
)
from open_notebook.ai.models import DefaultModels, Model
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


# =============================================================================
# Model Discovery Response Models
# =============================================================================


class DiscoveredModelResponse(BaseModel):
    """Response model for a discovered model."""

    name: str
    provider: str
    model_type: str
    description: Optional[str] = None


class ProviderSyncResponse(BaseModel):
    """Response model for provider sync operation."""

    provider: str
    discovered: int
    new: int
    existing: int


class AllProvidersSyncResponse(BaseModel):
    """Response model for syncing all providers."""

    results: Dict[str, ProviderSyncResponse]
    total_discovered: int
    total_new: int


class ProviderModelCountResponse(BaseModel):
    """Response model for provider model counts."""

    provider: str
    counts: Dict[str, int]
    total: int


class AutoAssignResult(BaseModel):
    """Response model for auto-assign operation."""

    assigned: Dict[str, str]  # slot_name -> model_id
    skipped: List[str]  # slots already assigned
    missing: List[str]  # slots with no available models


# Provider priority for auto-assignment (higher priority first)
PROVIDER_PRIORITY = [
    "openai",
    "anthropic",
    "google",
    "mistral",
    "groq",
    "deepseek",
    "xai",
    "openrouter",
    "ollama",
    "azure",
    "openai_compatible",
]

# Model preference patterns (preferred models within each provider)
MODEL_PREFERENCES = {
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-sonnet"],
    "google": ["gemini-2.0", "gemini-1.5-pro", "gemini-pro"],
    "mistral": ["mistral-large", "mixtral"],
    "groq": ["llama-3.3", "llama-3.1", "mixtral"],
}


async def _check_azure_support_db() -> bool:
    """Check if Azure is configured in ProviderConfig."""
    from open_notebook.domain.provider_config import ProviderConfig
    try:
        config = await ProviderConfig.get_instance()
        default_cred = config.get_default_config("azure")
        if default_cred:
            return bool(default_cred.api_key and default_cred.endpoint and default_cred.api_version)
    except Exception:
        pass
    return False


async def _check_openai_compatible_support_db() -> bool:
    """Check if OpenAI-compatible is configured in ProviderConfig."""
    from open_notebook.domain.provider_config import ProviderConfig
    try:
        config = await ProviderConfig.get_instance()
        default_cred = config.get_default_config("openai_compatible")
        if default_cred:
            return bool(default_cred.base_url or (default_cred.api_key and default_cred.api_key.get_secret_value()))
    except Exception:
        pass
    return False


async def _check_azure_support_db_mode(mode: str) -> bool:
    """Check if Azure is configured in ProviderConfig for a specific mode."""
    from open_notebook.domain.provider_config import ProviderConfig
    try:
        config = await ProviderConfig.get_instance()
        default_cred = config.get_default_config("azure")
        if default_cred:
            # For now, just check if the provider has any config
            return bool(default_cred.api_key and default_cred.endpoint and default_cred.api_version)
    except Exception:
        pass
    return False


async def _check_openai_compatible_support_db_mode(mode: str) -> bool:
    """Check if OpenAI-compatible is configured in ProviderConfig for a specific mode."""
    from open_notebook.domain.provider_config import ProviderConfig
    try:
        config = await ProviderConfig.get_instance()
        default_cred = config.get_default_config("openai_compatible")
        if default_cred:
            return bool(default_cred.base_url or (default_cred.api_key and default_cred.api_key.get_secret_value()))
    except Exception:
        pass
    return False


def _check_azure_support(mode: str) -> bool:
    """
    Check if Azure OpenAI provider is available for a specific mode.

    Args:
        mode: One of 'LLM', 'EMBEDDING', 'STT', 'TTS'

    Returns:
        bool: True if either generic or mode-specific env vars are set
    """
    # Check generic configuration (applies to all modes)
    generic = (
        os.environ.get("AZURE_OPENAI_API_KEY") is not None
        and os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
        and os.environ.get("AZURE_OPENAI_API_VERSION") is not None
    )

    # Check mode-specific configuration (takes precedence)
    specific = (
        os.environ.get(f"AZURE_OPENAI_API_KEY_{mode}") is not None
        and os.environ.get(f"AZURE_OPENAI_ENDPOINT_{mode}") is not None
        and os.environ.get(f"AZURE_OPENAI_API_VERSION_{mode}") is not None
    )

    return generic or specific


def _check_openai_compatible_support(mode: str) -> bool:
    """
    Check if OpenAI-compatible provider is available for a specific mode.

    Args:
        mode: One of 'LLM', 'EMBEDDING', 'STT', 'TTS'

    Returns:
        bool: True if either generic or mode-specific env var is set
    """
    generic = os.environ.get("OPENAI_COMPATIBLE_BASE_URL") is not None
    specific = os.environ.get(f"OPENAI_COMPATIBLE_BASE_URL_{mode}") is not None
    generic_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY") is not None
    specific_key = os.environ.get(f"OPENAI_COMPATIBLE_API_KEY_{mode}") is not None
    return generic or specific or generic_key or specific_key


@router.get("/models", response_model=List[ModelResponse])
async def get_models(
    type: Optional[str] = Query(None, description="Filter by model type"),
):
    """Get all configured models with optional type filtering."""
    try:
        if type:
            models = await Model.get_models_by_type(type)
        else:
            models = await Model.get_all()

        return [
            ModelResponse(
                id=model.id,
                name=model.name,
                provider=model.provider,
                type=model.type,
                created=str(model.created),
                updated=str(model.updated),
            )
            for model in models
        ]
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")


@router.post("/models", response_model=ModelResponse)
async def create_model(model_data: ModelCreate):
    """Create a new model configuration."""
    try:
        # Validate model type
        valid_types = ["language", "embedding", "text_to_speech", "speech_to_text"]
        if model_data.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type. Must be one of: {valid_types}",
            )

        # Check for duplicate model name under the same provider and type (case-insensitive)
        from open_notebook.database.repository import repo_query

        existing = await repo_query(
            "SELECT * FROM model WHERE string::lowercase(provider) = $provider AND string::lowercase(name) = $name AND string::lowercase(type) = $type LIMIT 1",
            {
                "provider": model_data.provider.lower(),
                "name": model_data.name.lower(),
                "type": model_data.type.lower(),
            },
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_data.name}' already exists for provider '{model_data.provider}' with type '{model_data.type}'",
            )

        new_model = Model(
            name=model_data.name,
            provider=model_data.provider,
            type=model_data.type,
        )
        await new_model.save()

        return ModelResponse(
            id=new_model.id or "",
            name=new_model.name,
            provider=new_model.provider,
            type=new_model.type,
            created=str(new_model.created),
            updated=str(new_model.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating model: {str(e)}")


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Delete a model configuration."""
    try:
        model = await Model.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        await model.delete()

        return {"message": "Model deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")


@router.get("/models/defaults", response_model=DefaultModelsResponse)
async def get_default_models():
    """Get default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()

        return DefaultModelsResponse(
            default_chat_model=defaults.default_chat_model,  # type: ignore[attr-defined]
            default_transformation_model=defaults.default_transformation_model,  # type: ignore[attr-defined]
            large_context_model=defaults.large_context_model,  # type: ignore[attr-defined]
            default_text_to_speech_model=defaults.default_text_to_speech_model,  # type: ignore[attr-defined]
            default_speech_to_text_model=defaults.default_speech_to_text_model,  # type: ignore[attr-defined]
            default_embedding_model=defaults.default_embedding_model,  # type: ignore[attr-defined]
            default_tools_model=defaults.default_tools_model,  # type: ignore[attr-defined]
        )
    except Exception as e:
        logger.error(f"Error fetching default models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching default models: {str(e)}"
        )


@router.put("/models/defaults", response_model=DefaultModelsResponse)
async def update_default_models(defaults_data: DefaultModelsResponse):
    """Update default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()

        # Update only provided fields
        if defaults_data.default_chat_model is not None:
            defaults.default_chat_model = defaults_data.default_chat_model  # type: ignore[attr-defined]
        if defaults_data.default_transformation_model is not None:
            defaults.default_transformation_model = (
                defaults_data.default_transformation_model
            )  # type: ignore[attr-defined]
        if defaults_data.large_context_model is not None:
            defaults.large_context_model = defaults_data.large_context_model  # type: ignore[attr-defined]
        if defaults_data.default_text_to_speech_model is not None:
            defaults.default_text_to_speech_model = (
                defaults_data.default_text_to_speech_model
            )  # type: ignore[attr-defined]
        if defaults_data.default_speech_to_text_model is not None:
            defaults.default_speech_to_text_model = (
                defaults_data.default_speech_to_text_model
            )  # type: ignore[attr-defined]
        if defaults_data.default_embedding_model is not None:
            defaults.default_embedding_model = defaults_data.default_embedding_model  # type: ignore[attr-defined]
        if defaults_data.default_tools_model is not None:
            defaults.default_tools_model = defaults_data.default_tools_model  # type: ignore[attr-defined]

        await defaults.update()

        # No cache refresh needed - next access will fetch fresh data from DB

        return DefaultModelsResponse(
            default_chat_model=defaults.default_chat_model,  # type: ignore[attr-defined]
            default_transformation_model=defaults.default_transformation_model,  # type: ignore[attr-defined]
            large_context_model=defaults.large_context_model,  # type: ignore[attr-defined]
            default_text_to_speech_model=defaults.default_text_to_speech_model,  # type: ignore[attr-defined]
            default_speech_to_text_model=defaults.default_speech_to_text_model,  # type: ignore[attr-defined]
            default_embedding_model=defaults.default_embedding_model,  # type: ignore[attr-defined]
            default_tools_model=defaults.default_tools_model,  # type: ignore[attr-defined]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating default models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating default models: {str(e)}"
        )


@router.get("/models/providers", response_model=ProviderAvailabilityResponse)
async def get_provider_availability():
    """Get provider availability based on database config and environment variables."""
    try:
        # Check DB configuration for azure and openai-compatible first
        azure_db = await _check_azure_support_db()
        openai_compatible_db = await _check_openai_compatible_support_db()

        # Check which providers have API keys configured (check both DB and env vars)
        # Use get_api_key() which checks DB first, then falls back to env var
        # This avoids mutating global os.environ state

        provider_status = {
            "ollama": os.environ.get("OLLAMA_API_BASE") is not None or await get_api_key("ollama") is not None,
            "openai": await get_api_key("openai") is not None,
            "groq": await get_api_key("groq") is not None,
            "xai": await get_api_key("xai") is not None,
            "vertex": (
                await get_api_key("vertex") is not None  # This checks all vertex fields
            ),
            "google": (
                await get_api_key("google") is not None
                or os.environ.get("GEMINI_API_KEY") is not None
            ),
            "openrouter": await get_api_key("openrouter") is not None,
            "anthropic": await get_api_key("anthropic") is not None,
            "elevenlabs": await get_api_key("elevenlabs") is not None,
            "voyage": await get_api_key("voyage") is not None,
            "azure": azure_db or (
                _check_azure_support("LLM")
                or _check_azure_support("EMBEDDING")
                or _check_azure_support("STT")
                or _check_azure_support("TTS")
            ),
            "mistral": await get_api_key("mistral") is not None,
            "deepseek": await get_api_key("deepseek") is not None,
            "openai-compatible": openai_compatible_db or (
                _check_openai_compatible_support("LLM")
                or _check_openai_compatible_support("EMBEDDING")
                or _check_openai_compatible_support("STT")
                or _check_openai_compatible_support("TTS")
            ),
        }

        available_providers = [k for k, v in provider_status.items() if v]
        unavailable_providers = [k for k, v in provider_status.items() if not v]

        # Get supported model types from Esperanto
        esperanto_available = AIFactory.get_available_providers()

        # Build supported types mapping only for available providers
        supported_types: dict[str, list[str]] = {}
        for provider in available_providers:
            supported_types[provider] = []

            # Map Esperanto model types to our environment variable modes
            mode_mapping = {
                "language": "LLM",
                "embedding": "EMBEDDING",
                "speech_to_text": "STT",
                "text_to_speech": "TTS",
            }

            # Special handling for openai-compatible to check mode-specific availability
            if provider == "openai-compatible":
                for model_type, mode in mode_mapping.items():
                    if (
                        model_type in esperanto_available
                        and provider in esperanto_available[model_type]
                    ):
                        # Check both DB config and env vars
                        db_mode = await _check_openai_compatible_support_db_mode(mode)
                        env_mode = _check_openai_compatible_support(mode)
                        if db_mode or env_mode:
                            supported_types[provider].append(model_type)
            # Special handling for azure to check mode-specific availability
            elif provider == "azure":
                for model_type, mode in mode_mapping.items():
                    if (
                        model_type in esperanto_available
                        and provider in esperanto_available[model_type]
                    ):
                        # Check both DB config and env vars
                        db_mode = await _check_azure_support_db_mode(mode)
                        env_mode = _check_azure_support(mode)
                        if db_mode or env_mode:
                            supported_types[provider].append(model_type)
            else:
                # Standard provider detection
                for model_type, providers in esperanto_available.items():
                    if provider in providers:
                        supported_types[provider].append(model_type)

        return ProviderAvailabilityResponse(
            available=available_providers,
            unavailable=unavailable_providers,
            supported_types=supported_types,
        )
    except Exception as e:
        logger.error(f"Error checking provider availability: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error checking provider availability: {str(e)}"
        )


# =============================================================================
# Model Discovery Endpoints
# =============================================================================


@router.get(
    "/models/discover/{provider}", response_model=List[DiscoveredModelResponse]
)
async def discover_models(provider: str):
    """
    Discover available models from a provider without registering them.

    This endpoint queries the provider's API to list available models
    but does not save them to the database. Use the sync endpoint
    to both discover and register models.
    """
    try:
        # Provision keys for this specific provider (not all keys)
        from open_notebook.ai.key_provider import provision_provider_keys
        await provision_provider_keys(provider)

        discovered = await discover_provider_models(provider)
        return [
            DiscoveredModelResponse(
                name=m.name,
                provider=m.provider,
                model_type=m.model_type,
                description=m.description,
            )
            for m in discovered
        ]
    except Exception as e:
        logger.error(f"Error discovering models for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error discovering models. Check server logs for details."
        )


@router.post("/models/sync/{provider}", response_model=ProviderSyncResponse)
async def sync_models(provider: str):
    """
    Sync models for a specific provider.

    Discovers available models from the provider's API and registers
    any new models in the database. Existing models are skipped.

    Returns counts of discovered, new, and existing models.
    """
    try:
        # Provision keys for this specific provider (not all keys)
        from open_notebook.ai.key_provider import provision_provider_keys
        await provision_provider_keys(provider)

        discovered, new, existing = await sync_provider_models(
            provider, auto_register=True
        )
        return ProviderSyncResponse(
            provider=provider,
            discovered=discovered,
            new=new,
            existing=existing,
        )
    except Exception as e:
        logger.error(f"Error syncing models for {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error syncing models. Check server logs for details.")


@router.post("/models/sync", response_model=AllProvidersSyncResponse)
async def sync_all_models():
    """
    Sync models for all configured providers.

    Discovers and registers models from all providers that have
    valid API keys configured. This is useful for initial setup
    or periodic refresh of available models.
    """
    try:
        # Provision all keys from database to environment variables
        from open_notebook.ai.key_provider import provision_all_keys
        await provision_all_keys()

        results = await sync_all_providers()

        response_results = {}
        total_discovered = 0
        total_new = 0

        for provider, (discovered, new, existing) in results.items():
            response_results[provider] = ProviderSyncResponse(
                provider=provider,
                discovered=discovered,
                new=new,
                existing=existing,
            )
            total_discovered += discovered
            total_new += new

        return AllProvidersSyncResponse(
            results=response_results,
            total_discovered=total_discovered,
            total_new=total_new,
        )
    except Exception as e:
        logger.error(f"Error syncing all models: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error syncing all models: {str(e)}"
        )


@router.get("/models/count/{provider}", response_model=ProviderModelCountResponse)
async def get_model_count(provider: str):
    """
    Get count of registered models for a provider, grouped by type.

    Returns counts for each model type (language, embedding,
    speech_to_text, text_to_speech) as well as total count.
    """
    try:
        counts = await get_provider_model_count(provider)
        total = sum(counts.values())
        return ProviderModelCountResponse(
            provider=provider,
            counts=counts,
            total=total,
        )
    except Exception as e:
        logger.error(f"Error getting model count for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting model count: {str(e)}"
        )


@router.get("/models/by-provider/{provider}", response_model=List[ModelResponse])
async def get_models_by_provider(provider: str):
    """
    Get all registered models for a specific provider.

    Returns models from the database that belong to the specified provider.
    """
    try:
        from open_notebook.database.repository import repo_query

        models = await repo_query(
            "SELECT * FROM model WHERE provider = $provider ORDER BY type, name",
            {"provider": provider},
        )

        return [
            ModelResponse(
                id=model.get("id", ""),
                name=model.get("name", ""),
                provider=model.get("provider", ""),
                type=model.get("type", ""),
                created=str(model.get("created", "")),
                updated=str(model.get("updated", "")),
            )
            for model in models
        ]
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching models: {str(e)}"
        )


def _get_preferred_model(
    models: List[Dict], provider_priority: List[str], model_preferences: Dict
) -> Optional[Dict]:
    """
    Select the best model from a list based on provider priority and model preferences.

    Args:
        models: List of model dictionaries with 'provider', 'name', 'id' keys
        provider_priority: List of providers in preference order
        model_preferences: Dict mapping provider to list of preferred model name patterns

    Returns:
        The best model dict, or None if no models available
    """
    if not models:
        return None

    # Group models by provider
    by_provider: Dict[str, List[Dict]] = {}
    for model in models:
        provider = model.get("provider", "")
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)

    # Find first provider with models (in priority order)
    for provider in provider_priority:
        if provider in by_provider:
            provider_models = by_provider[provider]

            # Check for preferred models within this provider
            if provider in model_preferences:
                for preference in model_preferences[provider]:
                    for model in provider_models:
                        if preference.lower() in model.get("name", "").lower():
                            return model

            # Fall back to first model from this provider
            return provider_models[0]

    # Fall back to first model from any provider
    return models[0] if models else None


@router.post("/models/auto-assign", response_model=AutoAssignResult)
async def auto_assign_defaults():
    """
    Auto-assign default models based on available models.

    This endpoint intelligently assigns the first available model of each
    required type to the corresponding default slot. It uses provider
    priority (preferring premium providers like OpenAI, Anthropic) and
    model preferences within each provider.

    Returns:
        - assigned: Dict of slot names to assigned model IDs
        - skipped: List of slots that already have models assigned
        - missing: List of slots with no available models
    """
    try:
        from open_notebook.database.repository import repo_query

        # Get current defaults
        defaults = await DefaultModels.get_instance()

        # Get all models grouped by type
        all_models = await repo_query(
            "SELECT * FROM model ORDER BY provider, name",
            {},
        )

        # Group models by type
        models_by_type: Dict[str, List[Dict]] = {
            "language": [],
            "embedding": [],
            "text_to_speech": [],
            "speech_to_text": [],
        }

        for model in all_models:
            model_type = model.get("type", "")
            if model_type in models_by_type:
                models_by_type[model_type].append(model)

        # Define slot configuration: (slot_name, model_type, current_value)
        slot_configs = [
            ("default_chat_model", "language", defaults.default_chat_model),  # type: ignore[attr-defined]
            ("default_transformation_model", "language", defaults.default_transformation_model),  # type: ignore[attr-defined]
            ("default_tools_model", "language", defaults.default_tools_model),  # type: ignore[attr-defined]
            ("large_context_model", "language", defaults.large_context_model),  # type: ignore[attr-defined]
            ("default_embedding_model", "embedding", defaults.default_embedding_model),  # type: ignore[attr-defined]
            ("default_text_to_speech_model", "text_to_speech", defaults.default_text_to_speech_model),  # type: ignore[attr-defined]
            ("default_speech_to_text_model", "speech_to_text", defaults.default_speech_to_text_model),  # type: ignore[attr-defined]
        ]

        assigned: Dict[str, str] = {}
        skipped: List[str] = []
        missing: List[str] = []

        for slot_name, model_type, current_value in slot_configs:
            if current_value:
                # Slot already has a value
                skipped.append(slot_name)
                continue

            available_models = models_by_type.get(model_type, [])
            if not available_models:
                # No models of this type available
                missing.append(slot_name)
                continue

            # Select best model for this slot
            best_model = _get_preferred_model(
                available_models, PROVIDER_PRIORITY, MODEL_PREFERENCES
            )

            if best_model:
                model_id = best_model.get("id", "")
                assigned[slot_name] = model_id
                # Update the defaults object
                setattr(defaults, slot_name, model_id)

        # Save updated defaults if any assignments were made
        if assigned:
            await defaults.update()

        return AutoAssignResult(
            assigned=assigned,
            skipped=skipped,
            missing=missing,
        )

    except Exception as e:
        logger.error(f"Error auto-assigning defaults: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error auto-assigning defaults: {str(e)}"
        )
