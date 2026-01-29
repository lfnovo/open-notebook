"""
API Key Provider - Database-first with environment fallback.

This module provides a unified interface for retrieving API keys and provider
configuration. It checks the database (APIKeyConfig) first, then falls back
to environment variables for backward compatibility.

Usage:
    from open_notebook.ai.key_provider import provision_provider_keys

    # Call before model provisioning to set env vars from DB
    await provision_provider_keys("openai")
"""

import os
from typing import Optional

from loguru import logger

from open_notebook.domain.api_key_config import APIKeyConfig

# =============================================================================
# Provider Configuration Mapping
# =============================================================================
# Maps provider names to their environment variable names and APIKeyConfig fields.
# This is the single source of truth for provider-to-env-var mapping.

PROVIDER_CONFIG = {
    # Simple providers (just API key)
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "config_field": "openai_api_key",
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "config_field": "anthropic_api_key",
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
        "config_field": "google_api_key",
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        "config_field": "groq_api_key",
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
        "config_field": "mistral_api_key",
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "config_field": "deepseek_api_key",
    },
    "xai": {
        "env_var": "XAI_API_KEY",
        "config_field": "xai_api_key",
    },
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
        "config_field": "openrouter_api_key",
    },
    "voyage": {
        "env_var": "VOYAGE_API_KEY",
        "config_field": "voyage_api_key",
    },
    "elevenlabs": {
        "env_var": "ELEVENLABS_API_KEY",
        "config_field": "elevenlabs_api_key",
    },
    # URL-based providers
    "ollama": {
        "env_var": "OLLAMA_API_BASE",
        "config_field": "ollama_api_base",
    },
}

# Vertex AI configuration (multiple fields)
VERTEX_CONFIG = {
    "project": {
        "env_var": "VERTEX_PROJECT",
        "config_field": "vertex_project",
    },
    "location": {
        "env_var": "VERTEX_LOCATION",
        "config_field": "vertex_location",
    },
    "credentials": {
        "env_var": "GOOGLE_APPLICATION_CREDENTIALS",
        "config_field": "google_application_credentials",
    },
}

# Azure OpenAI configuration (generic + mode-specific)
AZURE_CONFIG = {
    "api_key": {
        "env_var": "AZURE_OPENAI_API_KEY",
        "config_field": "azure_openai_api_key",
    },
    "api_version": {
        "env_var": "AZURE_OPENAI_API_VERSION",
        "config_field": "azure_openai_api_version",
    },
    "endpoint": {
        "env_var": "AZURE_OPENAI_ENDPOINT",
        "config_field": "azure_openai_endpoint",
    },
    # Mode-specific endpoints (LLM, EMBEDDING, STT, TTS)
    "endpoint_llm": {
        "env_var": "AZURE_OPENAI_ENDPOINT_LLM",
        "config_field": "azure_openai_endpoint_llm",
    },
    "endpoint_embedding": {
        "env_var": "AZURE_OPENAI_ENDPOINT_EMBEDDING",
        "config_field": "azure_openai_endpoint_embedding",
    },
    "endpoint_stt": {
        "env_var": "AZURE_OPENAI_ENDPOINT_STT",
        "config_field": "azure_openai_endpoint_stt",
    },
    "endpoint_tts": {
        "env_var": "AZURE_OPENAI_ENDPOINT_TTS",
        "config_field": "azure_openai_endpoint_tts",
    },
}

# OpenAI-Compatible configuration (generic + mode-specific)
OPENAI_COMPATIBLE_CONFIG = {
    # Generic
    "api_key": {
        "env_var": "OPENAI_COMPATIBLE_API_KEY",
        "config_field": "openai_compatible_api_key",
    },
    "base_url": {
        "env_var": "OPENAI_COMPATIBLE_BASE_URL",
        "config_field": "openai_compatible_base_url",
    },
    # Mode-specific: LLM
    "api_key_llm": {
        "env_var": "OPENAI_COMPATIBLE_API_KEY_LLM",
        "config_field": "openai_compatible_api_key_llm",
    },
    "base_url_llm": {
        "env_var": "OPENAI_COMPATIBLE_BASE_URL_LLM",
        "config_field": "openai_compatible_base_url_llm",
    },
    # Mode-specific: Embedding
    "api_key_embedding": {
        "env_var": "OPENAI_COMPATIBLE_API_KEY_EMBEDDING",
        "config_field": "openai_compatible_api_key_embedding",
    },
    "base_url_embedding": {
        "env_var": "OPENAI_COMPATIBLE_BASE_URL_EMBEDDING",
        "config_field": "openai_compatible_base_url_embedding",
    },
    # Mode-specific: STT
    "api_key_stt": {
        "env_var": "OPENAI_COMPATIBLE_API_KEY_STT",
        "config_field": "openai_compatible_api_key_stt",
    },
    "base_url_stt": {
        "env_var": "OPENAI_COMPATIBLE_BASE_URL_STT",
        "config_field": "openai_compatible_base_url_stt",
    },
    # Mode-specific: TTS
    "api_key_tts": {
        "env_var": "OPENAI_COMPATIBLE_API_KEY_TTS",
        "config_field": "openai_compatible_api_key_tts",
    },
    "base_url_tts": {
        "env_var": "OPENAI_COMPATIBLE_BASE_URL_TTS",
        "config_field": "openai_compatible_base_url_tts",
    },
}


async def get_api_key(provider: str) -> Optional[str]:
    """
    Get API key for a provider. Checks database first, then env var.

    Args:
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        API key string or None if not configured
    """
    config_info = PROVIDER_CONFIG.get(provider)
    if not config_info:
        return None

    # Try database first
    try:
        api_config = await APIKeyConfig.get_instance()
        db_value = getattr(api_config, config_info["config_field"], None)
        if db_value:
            # Handle SecretStr (API keys) vs regular strings (URLs)
            if hasattr(db_value, "get_secret_value"):
                key_value = db_value.get_secret_value()
            else:
                key_value = db_value

            if key_value:
                logger.debug(f"Using {provider} API key from database")
                return key_value
    except Exception as e:
        logger.debug(f"Could not load API key from database for {provider}: {e}")

    # Fall back to environment variable
    env_value = os.environ.get(config_info["env_var"])
    if env_value:
        logger.debug(f"Using {provider} API key from environment variable")
    return env_value


async def _provision_simple_provider(provider: str) -> bool:
    """
    Set environment variable for a simple provider from DB config.

    Returns:
        True if key was set from database, False otherwise
    """
    config_info = PROVIDER_CONFIG.get(provider)
    if not config_info:
        return False

    try:
        api_config = await APIKeyConfig.get_instance()
        db_value = getattr(api_config, config_info["config_field"], None)
        if db_value:
            # Handle SecretStr (API keys) vs regular strings (URLs)
            if hasattr(db_value, "get_secret_value"):
                key_value = db_value.get_secret_value()
            else:
                key_value = db_value

            if key_value:
                os.environ[config_info["env_var"]] = key_value
                logger.debug(f"Set {config_info['env_var']} from database")
                return True
    except Exception as e:
        logger.debug(f"Could not provision {provider} from database: {e}")

    return False


async def _provision_vertex() -> bool:
    """
    Set environment variables for Google Vertex AI from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False
    try:
        api_config = await APIKeyConfig.get_instance()
        for key, config in VERTEX_CONFIG.items():
            db_value = getattr(api_config, config["config_field"], None)
            if db_value:
                os.environ[config["env_var"]] = db_value
                logger.debug(f"Set {config['env_var']} from database")
                any_set = True
    except Exception as e:
        logger.debug(f"Could not provision vertex from database: {e}")

    return any_set


async def _provision_azure() -> bool:
    """
    Set environment variables for Azure OpenAI from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False
    try:
        api_config = await APIKeyConfig.get_instance()
        for key, config in AZURE_CONFIG.items():
            db_value = getattr(api_config, config["config_field"], None)
            if db_value:
                # Handle SecretStr for api_key
                if hasattr(db_value, "get_secret_value"):
                    value = db_value.get_secret_value()
                else:
                    value = db_value

                if value:
                    os.environ[config["env_var"]] = value
                    logger.debug(f"Set {config['env_var']} from database")
                    any_set = True
    except Exception as e:
        logger.debug(f"Could not provision azure from database: {e}")

    return any_set


async def _provision_openai_compatible() -> bool:
    """
    Set environment variables for OpenAI-Compatible providers from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False
    try:
        api_config = await APIKeyConfig.get_instance()
        for key, config in OPENAI_COMPATIBLE_CONFIG.items():
            db_value = getattr(api_config, config["config_field"], None)
            if db_value:
                # Handle SecretStr for api_key fields
                if hasattr(db_value, "get_secret_value"):
                    value = db_value.get_secret_value()
                else:
                    value = db_value

                if value:
                    os.environ[config["env_var"]] = value
                    logger.debug(f"Set {config['env_var']} from database")
                    any_set = True
    except Exception as e:
        logger.debug(f"Could not provision openai-compatible from database: {e}")

    return any_set


async def provision_provider_keys(provider: str) -> bool:
    """
    Provision environment variables from database for a specific provider.

    This function checks if the provider has configuration stored in the database
    and sets the corresponding environment variables. If the database doesn't have
    the configuration, existing environment variables remain unchanged.

    This is the main entry point for the DB→Env fallback mechanism.

    Args:
        provider: Provider name (openai, anthropic, azure, vertex,
                  openai-compatible, etc.)

    Returns:
        True if any keys were set from database, False otherwise

    Example:
        # Before provisioning a model, ensure DB keys are in env vars
        await provision_provider_keys("openai")
        model = AIFactory.create_language(model_name="gpt-4", provider="openai")
    """
    # Normalize provider name
    provider_lower = provider.lower()

    # Handle complex providers with multiple config fields
    if provider_lower == "vertex":
        return await _provision_vertex()
    elif provider_lower == "azure":
        return await _provision_azure()
    elif provider_lower in ("openai-compatible", "openai_compatible"):
        return await _provision_openai_compatible()

    # Handle simple providers
    return await _provision_simple_provider(provider_lower)


async def provision_all_keys() -> dict[str, bool]:
    """
    Provision environment variables from database for all providers.

    Useful at application startup to load all DB-stored keys into environment.

    Returns:
        Dict mapping provider names to whether keys were set from DB
    """
    results: dict[str, bool] = {}

    # Simple providers
    for provider in PROVIDER_CONFIG.keys():
        results[provider] = await provision_provider_keys(provider)

    # Complex providers
    results["vertex"] = await provision_provider_keys("vertex")
    results["azure"] = await provision_provider_keys("azure")
    results["openai_compatible"] = await provision_provider_keys("openai_compatible")

    return results
