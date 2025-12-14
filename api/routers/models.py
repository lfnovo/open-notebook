import os
from typing import Any, Dict, List, Optional

import httpx
from esperanto import AIFactory
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import (
    DefaultModelsResponse,
    ModelCreate,
    ModelResponse,
    ProviderAvailabilityResponse,
)
from open_notebook.domain.models import DefaultModels, Model
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


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
    return generic or specific


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


@router.get("/models", response_model=List[ModelResponse])
async def get_models(
    type: Optional[str] = Query(None, description="Filter by model type")
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
                detail=f"Invalid model type. Must be one of: {valid_types}"
            )

        # Check for duplicate model name under the same provider (case-insensitive)
        from open_notebook.database.repository import repo_query
        existing = await repo_query(
            "SELECT * FROM model WHERE string::lowercase(provider) = $provider AND string::lowercase(name) = $name LIMIT 1",
            {"provider": model_data.provider.lower(), "name": model_data.name.lower()}
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_data.name}' already exists for provider '{model_data.provider}'"
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
        raise HTTPException(status_code=500, detail=f"Error fetching default models: {str(e)}")


@router.put("/models/defaults", response_model=DefaultModelsResponse)
async def update_default_models(defaults_data: DefaultModelsResponse):
    """Update default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()
        
        # Update only provided fields
        if defaults_data.default_chat_model is not None:
            defaults.default_chat_model = defaults_data.default_chat_model  # type: ignore[attr-defined]
        if defaults_data.default_transformation_model is not None:
            defaults.default_transformation_model = defaults_data.default_transformation_model  # type: ignore[attr-defined]
        if defaults_data.large_context_model is not None:
            defaults.large_context_model = defaults_data.large_context_model  # type: ignore[attr-defined]
        if defaults_data.default_text_to_speech_model is not None:
            defaults.default_text_to_speech_model = defaults_data.default_text_to_speech_model  # type: ignore[attr-defined]
        if defaults_data.default_speech_to_text_model is not None:
            defaults.default_speech_to_text_model = defaults_data.default_speech_to_text_model  # type: ignore[attr-defined]
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
        raise HTTPException(status_code=500, detail=f"Error updating default models: {str(e)}")


@router.get("/models/providers", response_model=ProviderAvailabilityResponse)
async def get_provider_availability():
    """Get provider availability based on environment variables."""
    try:
        # Check which providers have API keys configured
        provider_status = {
            "ollama": os.environ.get("OLLAMA_API_BASE") is not None,
            "openai": os.environ.get("OPENAI_API_KEY") is not None,
            "groq": os.environ.get("GROQ_API_KEY") is not None,
            "xai": os.environ.get("XAI_API_KEY") is not None,
            "vertex": (
                os.environ.get("VERTEX_PROJECT") is not None
                and os.environ.get("VERTEX_LOCATION") is not None
                and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
            ),
            "google": (
                os.environ.get("GOOGLE_API_KEY") is not None
                or os.environ.get("GEMINI_API_KEY") is not None
            ),
            "openrouter": os.environ.get("OPENROUTER_API_KEY") is not None,
            "anthropic": os.environ.get("ANTHROPIC_API_KEY") is not None,
            "elevenlabs": os.environ.get("ELEVENLABS_API_KEY") is not None,
            "voyage": os.environ.get("VOYAGE_API_KEY") is not None,
            "azure": (
                _check_azure_support("LLM")
                or _check_azure_support("EMBEDDING")
                or _check_azure_support("STT")
                or _check_azure_support("TTS")
            ),
            "mistral": os.environ.get("MISTRAL_API_KEY") is not None,
            "deepseek": os.environ.get("DEEPSEEK_API_KEY") is not None,
            "openai-compatible": (
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
                    if model_type in esperanto_available and provider in esperanto_available[model_type]:
                        if _check_openai_compatible_support(mode):
                            supported_types[provider].append(model_type)
            # Special handling for azure to check mode-specific availability
            elif provider == "azure":
                for model_type, mode in mode_mapping.items():
                    if model_type in esperanto_available and provider in esperanto_available[model_type]:
                        if _check_azure_support(mode):
                            supported_types[provider].append(model_type)
            else:
                # Standard provider detection
                for model_type, providers in esperanto_available.items():
                    if provider in providers:
                        supported_types[provider].append(model_type)
        
        return ProviderAvailabilityResponse(
            available=available_providers,
            unavailable=unavailable_providers,
            supported_types=supported_types
        )
    except Exception as e:
        logger.error(f"Error checking provider availability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking provider availability: {str(e)}")


@router.get("/models/ollama/available")
async def get_available_ollama_models() -> Dict[str, Any]:
    """Get list of models available in Ollama instance."""
    try:
        ollama_base = os.environ.get("OLLAMA_API_BASE")
        if not ollama_base:
            raise HTTPException(
                status_code=503, 
                detail="Ollama is not configured. Set OLLAMA_API_BASE environment variable."
            )
        
        # Call Ollama API to list models
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{ollama_base}/api/tags")
                response.raise_for_status()
                data = response.json()
                
                models = []
                if "models" in data:
                    for model in data["models"]:
                        models.append({
                            "name": model.get("name", ""),
                            "size": model.get("size", 0),
                            "modified_at": model.get("modified_at", ""),
                            "digest": model.get("digest", "")
                        })
                
                return {
                    "available": True,
                    "models": models,
                    "base_url": ollama_base
                }
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail=f"Cannot connect to Ollama at {ollama_base}. Is Ollama running?"
                )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail=f"Ollama at {ollama_base} is not responding. Check if it's running."
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Ollama models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching Ollama models: {str(e)}")


@router.post("/models/ollama/sync")
async def sync_ollama_models() -> Dict[str, Any]:
    """Auto-sync Ollama models to database - adds new ones, doesn't remove existing."""
    try:
        ollama_base = os.environ.get("OLLAMA_API_BASE")
        if not ollama_base:
            raise HTTPException(
                status_code=503, 
                detail="Ollama is not configured. Set OLLAMA_API_BASE environment variable."
            )
        
        # Get models from Ollama
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{ollama_base}/api/tags")
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Cannot connect to Ollama: {str(e)}"
                )
        
        if "models" not in data:
            return {"synced": 0, "skipped": 0, "total": 0}
        
        synced = 0
        skipped = 0
        
        from open_notebook.database.repository import repo_query
        
        for ollama_model in data["models"]:
            model_name = ollama_model.get("name", "")
            if not model_name:
                continue
            
            # Determine model type based on name patterns
            model_type = "language"  # Default
            if "embed" in model_name.lower():
                model_type = "embedding"
            elif "whisper" in model_name.lower():
                model_type = "speech_to_text"
            
            # Check if model already exists (case-insensitive)
            existing = await repo_query(
                "SELECT * FROM model WHERE string::lowercase(provider) = 'ollama' AND string::lowercase(name) = $name LIMIT 1",
                {"name": model_name.lower()}
            )
            
            if existing:
                skipped += 1
                continue
            
            # Create new model
            new_model = Model(
                name=model_name,
                provider="ollama",
                type=model_type,
            )
            await new_model.save()
            synced += 1
            logger.info(f"Auto-synced Ollama model: {model_name} (type: {model_type})")
        
        return {
            "synced": synced,
            "skipped": skipped,
            "total": len(data["models"])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing Ollama models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing Ollama models: {str(e)}")


@router.get("/models/validate")
async def validate_configured_models() -> Dict[str, Any]:
    """Validate that configured default models exist in Ollama."""
    try:
        # Get default models - handle case where they don't exist yet
        try:
            defaults = await DefaultModels.get_defaults()
        except Exception as e:
            logger.warning(f"Could not get default models (may not be initialized yet): {e}")
            # Return empty validation if defaults not set up yet
            return {
                "valid": True,
                "missing_models": [],
                "available_ollama_models": [],
                "details": {}
            }
        
        # Get available Ollama models
        ollama_models = []
        ollama_base = os.environ.get("OLLAMA_API_BASE")
        
        if ollama_base:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(f"{ollama_base}/api/tags")
                    response.raise_for_status()
                    data = response.json()
                    if "models" in data:
                        ollama_models = [m.get("name", "") for m in data["models"]]
                except Exception as e:
                    logger.warning(f"Could not fetch Ollama models: {e}")
        
        # Check each configured model
        validation_results = {
            "chat_model": {
                "configured": defaults.default_chat_model,
                "available": defaults.default_chat_model in ollama_models if defaults.default_chat_model else None,
                "provider": "ollama" if defaults.default_chat_model and ":" in defaults.default_chat_model else "unknown"
            },
            "embedding_model": {
                "configured": defaults.default_embedding_model,
                "available": defaults.default_embedding_model in ollama_models if defaults.default_embedding_model else None,
                "provider": "ollama" if defaults.default_embedding_model and ":" in defaults.default_embedding_model else "unknown"
            },
            "transformation_model": {
                "configured": defaults.default_transformation_model,
                "available": defaults.default_transformation_model in ollama_models if defaults.default_transformation_model else None,
                "provider": "ollama" if defaults.default_transformation_model and ":" in defaults.default_transformation_model else "unknown"
            }
        }
        
        # Count issues
        missing_models = []
        for model_type, info in validation_results.items():
            if info["configured"] and info["available"] is False:
                missing_models.append({
                    "type": model_type,
                    "name": info["configured"]
                })
        
        return {
            "valid": len(missing_models) == 0,
            "missing_models": missing_models,
            "available_ollama_models": ollama_models,
            "details": validation_results
        }
    except Exception as e:
        logger.error(f"Error validating models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating models: {str(e)}")