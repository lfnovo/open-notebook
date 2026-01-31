"""
Model Discovery - Automatic model fetching from AI providers.

This module provides functionality to discover available models from configured
AI providers and automatically register them in the database.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger

from open_notebook.ai.key_provider import provision_provider_keys
from open_notebook.ai.models import Model
from open_notebook.database.repository import repo_query


@dataclass
class DiscoveredModel:
    """Represents a model discovered from a provider."""

    name: str
    provider: str
    model_type: str  # language, embedding, speech_to_text, text_to_speech
    description: Optional[str] = None


# =============================================================================
# Provider-Specific Model Type Classification
# =============================================================================
# These mappings help classify models by their capabilities based on naming patterns

OPENAI_MODEL_TYPES = {
    "language": [
        "gpt-4",
        "gpt-3.5",
        "o1",
        "o3",
        "chatgpt",
        "text-davinci",
        "davinci",
        "curie",
        "babbage",
        "ada",
    ],
    "embedding": ["text-embedding", "embedding"],
    "speech_to_text": ["whisper"],
    "text_to_speech": ["tts"],
}

ANTHROPIC_MODELS = {
    # Static list since Anthropic doesn't have a model listing API
    "language": [
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
}

GOOGLE_MODEL_TYPES = {
    "language": ["gemini", "palm", "bison", "chat"],
    "embedding": ["embedding", "textembedding"],
}

OLLAMA_MODEL_TYPES = {
    # Ollama models can do multiple things, classify by common names
    "language": [
        "llama",
        "mistral",
        "mixtral",
        "codellama",
        "phi",
        "gemma",
        "qwen",
        "deepseek",
        "vicuna",
        "falcon",
        "orca",
        "neural",
        "dolphin",
        "openchat",
        "starling",
        "solar",
        "yi",
        "nous",
        "wizard",
        "zephyr",
        "tinyllama",
    ],
    "embedding": ["nomic-embed", "mxbai-embed", "all-minilm", "bge-", "e5-"],
}

MISTRAL_MODEL_TYPES = {
    "language": [
        "mistral",
        "mixtral",
        "codestral",
        "ministral",
        "pixtral",
        "open-mistral",
        "open-mixtral",
    ],
    "embedding": ["mistral-embed"],
}

GROQ_MODEL_TYPES = {
    "language": ["llama", "mixtral", "gemma", "whisper"],
    "speech_to_text": ["whisper"],
}

DEEPSEEK_MODEL_TYPES = {
    "language": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
}

XAI_MODEL_TYPES = {
    "language": ["grok"],
}

VOYAGE_MODEL_TYPES = {
    "embedding": ["voyage"],
}

ELEVENLABS_MODEL_TYPES = {
    "text_to_speech": ["eleven"],
}


def classify_model_type(model_name: str, provider: str) -> str:
    """
    Classify a model into a type based on its name and provider.

    Returns one of: language, embedding, speech_to_text, text_to_speech
    """
    name_lower = model_name.lower()

    type_mappings = {
        "openai": OPENAI_MODEL_TYPES,
        "google": GOOGLE_MODEL_TYPES,
        "ollama": OLLAMA_MODEL_TYPES,
        "mistral": MISTRAL_MODEL_TYPES,
        "groq": GROQ_MODEL_TYPES,
        "deepseek": DEEPSEEK_MODEL_TYPES,
        "xai": XAI_MODEL_TYPES,
        "voyage": VOYAGE_MODEL_TYPES,
        "elevenlabs": ELEVENLABS_MODEL_TYPES,
    }

    mapping = type_mappings.get(provider, {})

    # Check each type in order of specificity
    for model_type in ["speech_to_text", "text_to_speech", "embedding", "language"]:
        patterns = mapping.get(model_type, [])
        for pattern in patterns:
            if pattern in name_lower:
                return model_type

    # Default to language for unknown models
    return "language"


# =============================================================================
# Provider-Specific Model Discovery Functions
# =============================================================================


async def discover_openai_models() -> List[DiscoveredModel]:
    """Fetch available models from OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_type = classify_model_type(model_id, "openai")
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="openai",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover OpenAI models: {e}")

    return models


async def discover_anthropic_models() -> List[DiscoveredModel]:
    """Return static list of Anthropic models (no discovery API available)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    # Anthropic doesn't have a model listing API, so we use a static list
    models = []
    for model_name in ANTHROPIC_MODELS.get("language", []):
        models.append(
            DiscoveredModel(
                name=model_name,
                provider="anthropic",
                model_type="language",
            )
        )
    return models


async def discover_google_models() -> List[DiscoveredModel]:
    """Fetch available models from Google Gemini API."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            # Build URL without logging the key to avoid exposure
            url = "https://generativelanguage.googleapis.com/v1/models"
            headers = {"X-Goog-Api-Key": api_key}
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            for model in data.get("models", []):
                # Google returns full path like "models/gemini-1.5-flash"
                model_name = model.get("name", "").replace("models/", "")
                if model_name:
                    model_type = classify_model_type(model_name, "google")
                    # Check supported generation methods for better classification
                    methods = model.get("supportedGenerationMethods", [])
                    if "embedContent" in methods:
                        model_type = "embedding"
                    elif "generateContent" in methods:
                        model_type = "language"

                    models.append(
                        DiscoveredModel(
                            name=model_name,
                            provider="google",
                            model_type=model_type,
                            description=model.get("displayName"),
                        )
                    )
    except Exception as e:
        # Log without exposing the API key in the message
        logger.warning(f"Failed to discover Google models: {type(e).__name__}")

    return models


async def discover_ollama_models() -> List[DiscoveredModel]:
    """Fetch available models from local Ollama instance."""
    base_url = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    if not base_url:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/api/tags",
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("models", []):
                model_name = model.get("name", "")
                if model_name:
                    model_type = classify_model_type(model_name, "ollama")
                    models.append(
                        DiscoveredModel(
                            name=model_name,
                            provider="ollama",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover Ollama models: {e}")

    return models


async def discover_groq_models() -> List[DiscoveredModel]:
    """Fetch available models from Groq API."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_type = classify_model_type(model_id, "groq")
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="groq",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover Groq models: {e}")

    return models


async def discover_mistral_models() -> List[DiscoveredModel]:
    """Fetch available models from Mistral API."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_type = classify_model_type(model_id, "mistral")
                    # Check capabilities if available
                    capabilities = model.get("capabilities", {})
                    if capabilities.get("completion_chat"):
                        model_type = "language"

                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="mistral",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover Mistral models: {e}")

    return models


async def discover_deepseek_models() -> List[DiscoveredModel]:
    """Fetch available models from DeepSeek API."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.deepseek.com/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_type = classify_model_type(model_id, "deepseek")
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="deepseek",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover DeepSeek models: {e}")

    return models


async def discover_xai_models() -> List[DiscoveredModel]:
    """Fetch available models from xAI API."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.x.ai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_type = classify_model_type(model_id, "xai")
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="xai",
                            model_type=model_type,
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover xAI models: {e}")

    return models


async def discover_openrouter_models() -> List[DiscoveredModel]:
    """Fetch available models from OpenRouter API."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    # OpenRouter models are typically language models
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="openrouter",
                            model_type="language",
                            description=model.get("name"),
                        )
                    )
    except Exception as e:
        logger.warning(f"Failed to discover OpenRouter models: {e}")

    return models


async def discover_voyage_models() -> List[DiscoveredModel]:
    """Return static list of Voyage AI models (embedding only)."""
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        return []

    # Voyage AI specializes in embeddings
    voyage_models = [
        "voyage-3",
        "voyage-3-lite",
        "voyage-code-3",
        "voyage-finance-2",
        "voyage-law-2",
        "voyage-multilingual-2",
    ]

    return [
        DiscoveredModel(name=m, provider="voyage", model_type="embedding")
        for m in voyage_models
    ]


async def discover_elevenlabs_models() -> List[DiscoveredModel]:
    """Return static list of ElevenLabs TTS models."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return []

    # ElevenLabs specializes in TTS
    elevenlabs_models = [
        "eleven_multilingual_v2",
        "eleven_turbo_v2_5",
        "eleven_turbo_v2",
        "eleven_monolingual_v1",
        "eleven_multilingual_v1",
    ]

    return [
        DiscoveredModel(name=m, provider="elevenlabs", model_type="text_to_speech")
        for m in elevenlabs_models
    ]


async def discover_openai_compatible_models() -> List[DiscoveredModel]:
    """
    Fetch available models from an OpenAI-compatible API endpoint.
    Uses the configured base_url from the database or environment variable.
    """
    from open_notebook.domain.provider_config import ProviderConfig

    api_key = None
    base_url = None

    # Try to get config from ProviderConfig database first
    try:
        config = await ProviderConfig.get_instance()
        default_cred = config.get_default_config("openai_compatible")
        if default_cred:
            if default_cred.api_key:
                api_key = default_cred.api_key.get_secret_value()
            if default_cred.base_url:
                base_url = default_cred.base_url.rstrip("/")
    except Exception as e:
        logger.warning(f"Failed to read openai_compatible config from ProviderConfig: {e}")

    # Fall back to environment variables
    if not api_key:
        api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
    if not base_url:
        base_url = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").rstrip("/")

    if not base_url:
        logger.warning("No base_url configured for openai_compatible provider")
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = await client.get(
                f"{base_url}/models",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    # Classify based on model name patterns
                    model_type = classify_model_type(model_id, "openai")
                    models.append(
                        DiscoveredModel(
                            name=model_id,
                            provider="openai_compatible",
                            model_type=model_type,
                        )
                    )
    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to discover openai_compatible models: HTTP {e.response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to discover openai_compatible models: {e}")

    return models


# =============================================================================
# Main Discovery Functions
# =============================================================================

# Map provider names to their discovery functions
PROVIDER_DISCOVERY_FUNCTIONS = {
    "openai": discover_openai_models,
    "anthropic": discover_anthropic_models,
    "google": discover_google_models,
    "ollama": discover_ollama_models,
    "groq": discover_groq_models,
    "mistral": discover_mistral_models,
    "deepseek": discover_deepseek_models,
    "xai": discover_xai_models,
    "openrouter": discover_openrouter_models,
    "voyage": discover_voyage_models,
    "elevenlabs": discover_elevenlabs_models,
    "openai_compatible": discover_openai_compatible_models,
    "azure": discover_openai_models,  # Azure uses OpenAI-compatible API
    "vertex": discover_google_models,  # Vertex uses Google API
}


async def discover_provider_models(provider: str) -> List[DiscoveredModel]:
    """
    Discover available models for a specific provider.

    Args:
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        List of discovered models
    """
    # Provision keys from database first
    await provision_provider_keys(provider)

    discover_func = PROVIDER_DISCOVERY_FUNCTIONS.get(provider)
    if not discover_func:
        logger.warning(f"No discovery function for provider: {provider}")
        return []

    return await discover_func()


async def sync_provider_models(
    provider: str, auto_register: bool = True
) -> Tuple[int, int, int]:
    """
    Sync models for a provider: discover and optionally register in database.

    Args:
        provider: Provider name
        auto_register: If True, automatically create Model records in database

    Returns:
        Tuple of (discovered_count, new_count, existing_count)
    """
    discovered = await discover_provider_models(provider)
    discovered_count = len(discovered)
    new_count = 0
    existing_count = 0

    if not auto_register:
        return discovered_count, 0, 0

    if not discovered:
        return 0, 0, 0

    # Batch fetch existing models to avoid N+1 query pattern
    try:
        existing_models = await repo_query(
            "SELECT string::lowercase(name) as name, string::lowercase(type) as type FROM model "
            "WHERE string::lowercase(provider) = $provider",
            {"provider": provider.lower()},
        )
        # Create a set of (name, type) tuples for O(1) lookup
        existing_keys = set()
        for m in existing_models:
            existing_keys.add((m.get("name", ""), m.get("type", "")))
    except Exception as e:
        logger.warning(f"Failed to fetch existing models for {provider}: {e}")
        existing_keys = set()

    for model in discovered:
        model_key = (model.name.lower(), model.model_type.lower())

        # Check if model already exists using pre-fetched data
        if model_key in existing_keys:
            existing_count += 1
            continue

        # Create new model
        try:
            new_model = Model(
                name=model.name,
                provider=model.provider,
                type=model.model_type,
            )
            await new_model.save()
            new_count += 1
            logger.info(f"Registered new model: {model.provider}/{model.name} ({model.model_type})")
        except Exception as e:
            logger.warning(f"Failed to register model {model.name}: {e}")

    logger.info(
        f"Synced {provider}: {discovered_count} discovered, "
        f"{new_count} new, {existing_count} existing"
    )
    return discovered_count, new_count, existing_count


async def sync_all_providers() -> Dict[str, Tuple[int, int, int]]:
    """
    Sync models for all configured providers.

    Returns:
        Dict mapping provider names to (discovered, new, existing) tuples
    """
    results = {}

    # Run discovery for all providers in parallel
    tasks = []
    providers = list(PROVIDER_DISCOVERY_FUNCTIONS.keys())

    for provider in providers:
        tasks.append(sync_provider_models(provider, auto_register=True))

    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    for provider, result in zip(providers, task_results):
        if isinstance(result, Exception):
            logger.error(f"Error syncing {provider}: {result}")
            results[provider] = (0, 0, 0)
        else:
            results[provider] = result

    return results


async def get_provider_model_count(provider: str) -> Dict[str, int]:
    """
    Get count of registered models for a provider, grouped by type.

    Args:
        provider: Provider name (case-insensitive)

    Returns:
        Dict mapping model type to count
    """
    # Use case-insensitive comparison by lowercasing the provider
    result = await repo_query(
        "SELECT type, count() as count FROM model WHERE string::lowercase(provider) = string::lowercase($provider) GROUP BY type",
        {"provider": provider},
    )

    counts = {
        "language": 0,
        "embedding": 0,
        "speech_to_text": 0,
        "text_to_speech": 0,
    }

    for row in result:
        model_type = row.get("type")
        count = row.get("count", 0)
        if model_type in counts:
            counts[model_type] = count

    return counts
