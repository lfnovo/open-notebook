"""
Model Discovery - Automatic model fetching from AI providers.

This module provides functionality to discover available models from configured
AI providers and automatically register them in the database.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

import httpx
from loguru import logger

from open_notebook.ai.models import Model
from open_notebook.database.repository import repo_query
from open_notebook.domain.credential import Credential


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

# Fallback list used only when Anthropic's model listing API
# (GET https://api.anthropic.com/v1/models) is unreachable or errors.
ANTHROPIC_FALLBACK_MODELS = [
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
]

GOOGLE_MODEL_TYPES = {
    "language": ["gemini", "palm", "bison", "chat"],
    "embedding": ["embedding", "textembedding"],
    # Gemini TTS preview models carry "tts" in the name (checked before language).
    # Google STT reuses plain Gemini names and can't be told apart by name, so it
    # has no pattern here — users assign the speech_to_text type manually.
    "text_to_speech": ["tts"],
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
    # Voxtral. TTS first by specificity: the "-tts" model must not be caught by
    # the broader STT names. classify_model_type checks speech_to_text before
    # text_to_speech, so STT patterns are the explicit non-tts model names.
    "text_to_speech": ["voxtral-mini-tts", "voxtral-tts"],
    "speech_to_text": ["voxtral-mini-latest", "voxtral-small-latest"],
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
    "speech_to_text": ["scribe"],
}

DEEPGRAM_MODEL_TYPES = {
    "text_to_speech": ["aura"],
}

DASHSCOPE_MODEL_TYPES = {
    "language": ["qwen"],
}

MINIMAX_MODEL_TYPES = {
    "language": ["minimax", "abab"],
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
        "deepgram": DEEPGRAM_MODEL_TYPES,
        "dashscope": DASHSCOPE_MODEL_TYPES,
        "minimax": MINIMAX_MODEL_TYPES,
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
# OpenAI-Compatible Provider Discovery (table-driven)
# =============================================================================
# All of these providers expose the same endpoint shape:
#   GET {url} with "Authorization: Bearer {key}" -> {"data": [{"id": ...}, ...]}
# Only the URL, the env var holding the key, and small per-provider quirks
# differ, so they share one generic discovery function driven by this table.


def _classify_mistral(model: dict) -> str:
    """Mistral quirk: trust the capabilities flag over name-based patterns."""
    if model.get("capabilities", {}).get("completion_chat"):
        return "language"
    return classify_model_type(model.get("id", ""), "mistral")


@dataclass(frozen=True)
class ProviderDiscoverySpec:
    """Spec for a provider with an OpenAI-compatible /models endpoint."""

    url: str
    env_var: str
    # Optional quirk hooks; defaults are classify_model_type(id, provider)
    # and no description.
    classify: Optional[Callable[[dict], str]] = None
    description: Optional[Callable[[dict], Optional[str]]] = None


OPENAI_COMPAT_PROVIDERS: Dict[str, ProviderDiscoverySpec] = {
    "openai": ProviderDiscoverySpec(
        url="https://api.openai.com/v1/models",
        env_var="OPENAI_API_KEY",
    ),
    "groq": ProviderDiscoverySpec(
        url="https://api.groq.com/openai/v1/models",
        env_var="GROQ_API_KEY",
    ),
    "mistral": ProviderDiscoverySpec(
        url="https://api.mistral.ai/v1/models",
        env_var="MISTRAL_API_KEY",
        classify=_classify_mistral,
    ),
    "deepseek": ProviderDiscoverySpec(
        url="https://api.deepseek.com/models",
        env_var="DEEPSEEK_API_KEY",
    ),
    "xai": ProviderDiscoverySpec(
        url="https://api.x.ai/v1/models",
        env_var="XAI_API_KEY",
    ),
    "openrouter": ProviderDiscoverySpec(
        url="https://openrouter.ai/api/v1/models",
        env_var="OPENROUTER_API_KEY",
        # OpenRouter models are typically language models
        classify=lambda model: "language",
        description=lambda model: model.get("name"),
    ),
    "dashscope": ProviderDiscoverySpec(
        url="https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        env_var="DASHSCOPE_API_KEY",
    ),
    "minimax": ProviderDiscoverySpec(
        url="https://api.minimax.io/v1/models",
        env_var="MINIMAX_API_KEY",
    ),
}


async def discover_openai_compatible_provider(provider: str) -> List[DiscoveredModel]:
    """Fetch available models from a provider with an OpenAI-compatible API."""
    spec = OPENAI_COMPAT_PROVIDERS[provider]
    api_key = os.environ.get(spec.env_var)
    if not api_key:
        return []

    models = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                spec.url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for model in data.get("data", []):
                model_id = model.get("id", "")
                if not model_id:
                    continue
                if spec.classify is not None:
                    model_type = spec.classify(model)
                else:
                    model_type = classify_model_type(model_id, provider)
                description = (
                    spec.description(model) if spec.description is not None else None
                )
                models.append(
                    DiscoveredModel(
                        name=model_id,
                        provider=provider,
                        model_type=model_type,
                        description=description,
                    )
                )
    except Exception as e:
        logger.warning(f"Failed to discover {provider} models: {e}")

    return models


def _make_openai_compat_discoverer(
    provider: str,
) -> Callable[[], Awaitable[List[DiscoveredModel]]]:
    async def _discover() -> List[DiscoveredModel]:
        return await discover_openai_compatible_provider(provider)

    _discover.__name__ = f"discover_{provider}_models"
    _discover.__doc__ = f"Fetch available models from the {provider} API."
    return _discover


# Kept as module-level names so existing imports/patches keep working.
discover_openai_models = _make_openai_compat_discoverer("openai")
discover_groq_models = _make_openai_compat_discoverer("groq")
discover_mistral_models = _make_openai_compat_discoverer("mistral")
discover_deepseek_models = _make_openai_compat_discoverer("deepseek")
discover_xai_models = _make_openai_compat_discoverer("xai")
discover_openrouter_models = _make_openai_compat_discoverer("openrouter")
discover_dashscope_models = _make_openai_compat_discoverer("dashscope")
discover_minimax_models = _make_openai_compat_discoverer("minimax")


# =============================================================================
# Bespoke Provider Discovery Functions
# =============================================================================


async def fetch_anthropic_model_ids(api_key: str) -> List[str]:
    """
    Fetch model ids from Anthropic's model listing API.

    Uses GET https://api.anthropic.com/v1/models with pagination
    (after_id/has_more cursors). Raises on any HTTP or network error —
    callers decide whether to fall back to ANTHROPIC_FALLBACK_MODELS.
    """
    model_ids: List[str] = []
    params: Dict[str, str] = {"limit": "100"}
    async with httpx.AsyncClient() as client:
        # Hard page cap as a safety net against a misbehaving cursor.
        for _ in range(20):
            response = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    model_ids.append(model_id)
            if not data.get("has_more") or not data.get("last_id"):
                break
            params["after_id"] = data["last_id"]
    return model_ids


async def discover_anthropic_models() -> List[DiscoveredModel]:
    """Fetch available models from Anthropic's model listing API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    try:
        model_names = await fetch_anthropic_model_ids(api_key)
    except Exception as e:
        logger.warning(
            f"Failed to discover Anthropic models, using static fallback: {e}"
        )
        model_names = list(ANTHROPIC_FALLBACK_MODELS)

    return [
        DiscoveredModel(
            name=model_name,
            provider="anthropic",
            model_type=classify_model_type(model_name, "anthropic"),
        )
        for model_name in model_names
    ]


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
                # Google returns full path like "models/gemini-2.5-flash"
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

    # ElevenLabs TTS models + the Scribe STT model
    elevenlabs_models = [
        "eleven_multilingual_v2",
        "eleven_turbo_v2_5",
        "eleven_turbo_v2",
        "eleven_monolingual_v1",
        "eleven_multilingual_v1",
    ]

    discovered = [
        DiscoveredModel(name=m, provider="elevenlabs", model_type="text_to_speech")
        for m in elevenlabs_models
    ]
    discovered.append(
        DiscoveredModel(
            name="scribe_v1", provider="elevenlabs", model_type="speech_to_text"
        )
    )
    return discovered


async def discover_deepgram_models() -> List[DiscoveredModel]:
    """Return a curated static list of Deepgram Aura TTS voices.

    Deepgram has no model-listing API and treats each voice as a model id.
    This is a representative subset of the Aura-2 English catalog; users can
    add any other voice manually via the custom-model input.
    """
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        return []

    deepgram_voices = [
        "aura-2-thalia-en",
        "aura-2-andromeda-en",
        "aura-2-helena-en",
        "aura-2-apollo-en",
        "aura-2-arcas-en",
        "aura-2-asteria-en",
        "aura-2-athena-en",
        "aura-2-hera-en",
        "aura-2-hermes-en",
        "aura-2-atlas-en",
    ]

    return [
        DiscoveredModel(name=m, provider="deepgram", model_type="text_to_speech")
        for m in deepgram_voices
    ]


async def discover_openai_compatible_models() -> List[DiscoveredModel]:
    """
    Fetch available models from an OpenAI-compatible API endpoint.
    Uses the configured base_url from the database or environment variable.
    """
    api_key = None
    base_url = None

    # Try to get config from Credential database first
    try:
        credentials = await Credential.get_by_provider("openai_compatible")
        if credentials:
            cred = credentials[0]
            config = cred.to_esperanto_config()
            api_key = config.get("api_key")
            base_url = config.get("base_url", "").rstrip("/")
    except Exception as e:
        logger.warning(f"Failed to read openai_compatible config from Credential: {e}")

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
    "deepgram": discover_deepgram_models,
    "openai_compatible": discover_openai_compatible_models,
    "dashscope": discover_dashscope_models,
    "minimax": discover_minimax_models,
    "azure": None,  # Azure requires credential-based discovery (different auth)
    "vertex": None,  # Vertex requires credential-based discovery (service account)
}


async def discover_provider_models(provider: str) -> List[DiscoveredModel]:
    """
    Discover available models for a specific provider.

    Args:
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        List of discovered models
    """
    discover_func = PROVIDER_DISCOVERY_FUNCTIONS.get(provider)
    if discover_func is None:
        if provider in PROVIDER_DISCOVERY_FUNCTIONS:
            logger.info(
                f"Provider '{provider}' requires credential-based discovery. "
                f"Use the /credentials/{{id}}/discover endpoint instead."
            )
        else:
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
