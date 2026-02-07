"""
API Key Provider - Database-first with environment fallback.

This module provides a unified interface for retrieving API keys and provider
configuration. It reads from ProviderConfig (single source of truth) and
falls back to environment variables for backward compatibility.

Usage:
    from open_notebook.ai.key_provider import provision_provider_keys

    # Call before model provisioning to set env vars from DB
    await provision_provider_keys("openai")
"""

import os
from typing import Optional

from loguru import logger

from open_notebook.domain.provider_config import ProviderConfig


# =============================================================================
# Provider Configuration Mapping
# =============================================================================
# Maps provider names to their environment variable names.
# This is the single source of truth for provider-to-env-var mapping.

PROVIDER_CONFIG = {
    # Simple providers (just API key)
    "openai": {
        "env_var": "OPENAI_API_KEY",
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
    },
    "mistral": {
        "env_var": "MISTRAL_API_KEY",
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
    },
    "xai": {
        "env_var": "XAI_API_KEY",
    },
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
    },
    "voyage": {
        "env_var": "VOYAGE_API_KEY",
    },
    "elevenlabs": {
        "env_var": "ELEVENLABS_API_KEY",
    },
    # URL-based providers
    "ollama": {
        "env_var": "OLLAMA_API_BASE",
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
    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config(provider)
        if default_cred and default_cred.api_key:
            logger.debug(f"Using {provider} API key from ProviderConfig")
            return default_cred.api_key.get_secret_value()
    except Exception as e:
        logger.debug(f"Could not load API key from ProviderConfig for {provider}: {e}")

    # Fall back to environment variable
    config_info = PROVIDER_CONFIG.get(provider.lower())
    if config_info:
        env_value = os.environ.get(config_info["env_var"])
        if env_value:
            logger.debug(f"Using {provider} API key from environment variable")
        return env_value

    return None


async def get_provider_configs(provider: str) -> list[dict]:
    """
    Get all configurations for a provider from ProviderConfig.

    Args:
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        List of configuration dicts, each containing id, name, is_default, etc.
        Does NOT include api_key for security.
    """
    provider_lower = provider.lower()

    try:
        config = await ProviderConfig.get_instance()
        credentials = config.credentials.get(provider_lower, [])

        result = []
        for cred in credentials:
            config_data = {
                "id": cred.id,
                "name": cred.name,
                "provider": cred.provider,
                "is_default": cred.is_default,
            }
            if cred.base_url:
                config_data["base_url"] = cred.base_url
            if cred.model:
                config_data["model"] = cred.model
            if cred.api_version:
                config_data["api_version"] = cred.api_version
            if cred.endpoint:
                config_data["endpoint"] = cred.endpoint
            if cred.endpoint_llm:
                config_data["endpoint_llm"] = cred.endpoint_llm
            if cred.endpoint_embedding:
                config_data["endpoint_embedding"] = cred.endpoint_embedding
            if cred.endpoint_stt:
                config_data["endpoint_stt"] = cred.endpoint_stt
            if cred.endpoint_tts:
                config_data["endpoint_tts"] = cred.endpoint_tts
            if cred.project:
                config_data["project"] = cred.project
            if cred.location:
                config_data["location"] = cred.location
            if cred.credentials_path:
                config_data["credentials_path"] = cred.credentials_path
            result.append(config_data)

        return result
    except Exception as e:
        logger.debug(f"Could not load provider configs from database for {provider}: {e}")
        return []


async def get_default_api_key(provider: str) -> Optional[str]:
    """
    Get the default API key for a provider from ProviderConfig.

    Args:
        provider: Provider name (openai, anthropic, etc.)

    Returns:
        API key string or None if not configured
    """
    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config(provider)
        if default_cred and default_cred.api_key:
            return default_cred.api_key.get_secret_value()
    except Exception as e:
        logger.debug(f"Could not load API key from ProviderConfig for {provider}: {e}")

    return None


async def _provision_simple_provider(provider: str) -> bool:
    """
    Set environment variable for a simple provider from DB config.

    Returns:
        True if key was set from database, False otherwise
    """
    provider_lower = provider.lower()
    config_info = PROVIDER_CONFIG.get(provider_lower)
    if not config_info:
        return False

    provider_upper = provider_lower.upper()

    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config(provider_lower)

        if default_cred:
            # Set API key
            if default_cred.api_key:
                os.environ[f"{provider_upper}_API_KEY"] = (
                    default_cred.api_key.get_secret_value()
                )
                logger.debug(f"Set {provider_upper}_API_KEY from ProviderConfig")

            # Set base URL if present
            if default_cred.base_url:
                os.environ[f"{provider_upper}_API_BASE"] = default_cred.base_url
                logger.debug(f"Set {provider_upper}_API_BASE from ProviderConfig")

            return True
    except Exception as e:
        logger.debug(f"Could not provision {provider} from ProviderConfig: {e}")

    return False


async def _provision_vertex() -> bool:
    """
    Set environment variables for Google Vertex AI from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False

    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config("vertex")

        if default_cred:
            if default_cred.project:
                os.environ["VERTEX_PROJECT"] = default_cred.project
                logger.debug("Set VERTEX_PROJECT from ProviderConfig")
                any_set = True
            if default_cred.location:
                os.environ["VERTEX_LOCATION"] = default_cred.location
                logger.debug("Set VERTEX_LOCATION from ProviderConfig")
                any_set = True
            if default_cred.credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                    default_cred.credentials_path
                )
                logger.debug("Set GOOGLE_APPLICATION_CREDENTIALS from ProviderConfig")
                any_set = True
    except Exception as e:
        logger.debug(f"Could not provision vertex from ProviderConfig: {e}")

    return any_set


async def _provision_azure() -> bool:
    """
    Set environment variables for Azure OpenAI from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False

    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config("azure")

        if default_cred:
            if default_cred.api_key:
                os.environ["AZURE_OPENAI_API_KEY"] = (
                    default_cred.api_key.get_secret_value()
                )
                logger.debug("Set AZURE_OPENAI_API_KEY from ProviderConfig")
                any_set = True
            if default_cred.api_version:
                os.environ["AZURE_OPENAI_API_VERSION"] = default_cred.api_version
                logger.debug("Set AZURE_OPENAI_API_VERSION from ProviderConfig")
                any_set = True
            if default_cred.endpoint:
                os.environ["AZURE_OPENAI_ENDPOINT"] = default_cred.endpoint
                logger.debug("Set AZURE_OPENAI_ENDPOINT from ProviderConfig")
                any_set = True
            if default_cred.endpoint_llm:
                os.environ["AZURE_OPENAI_ENDPOINT_LLM"] = default_cred.endpoint_llm
                logger.debug("Set AZURE_OPENAI_ENDPOINT_LLM from ProviderConfig")
                any_set = True
            if default_cred.endpoint_embedding:
                os.environ["AZURE_OPENAI_ENDPOINT_EMBEDDING"] = (
                    default_cred.endpoint_embedding
                )
                logger.debug("Set AZURE_OPENAI_ENDPOINT_EMBEDDING from ProviderConfig")
                any_set = True
            if default_cred.endpoint_stt:
                os.environ["AZURE_OPENAI_ENDPOINT_STT"] = default_cred.endpoint_stt
                logger.debug("Set AZURE_OPENAI_ENDPOINT_STT from ProviderConfig")
                any_set = True
            if default_cred.endpoint_tts:
                os.environ["AZURE_OPENAI_ENDPOINT_TTS"] = default_cred.endpoint_tts
                logger.debug("Set AZURE_OPENAI_ENDPOINT_TTS from ProviderConfig")
                any_set = True
    except Exception as e:
        logger.debug(f"Could not provision azure from ProviderConfig: {e}")

    return any_set


async def _provision_openai_compatible() -> bool:
    """
    Set environment variables for OpenAI-Compatible providers from DB config.

    Returns:
        True if any keys were set from database
    """
    any_set = False

    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config("openai_compatible")

        if default_cred:
            if default_cred.api_key:
                os.environ["OPENAI_COMPATIBLE_API_KEY"] = (
                    default_cred.api_key.get_secret_value()
                )
                logger.debug("Set OPENAI_COMPATIBLE_API_KEY from ProviderConfig")
                any_set = True
            if default_cred.base_url:
                os.environ["OPENAI_COMPATIBLE_BASE_URL"] = default_cred.base_url
                logger.debug("Set OPENAI_COMPATIBLE_BASE_URL from ProviderConfig")
                any_set = True
    except Exception as e:
        logger.debug(
            f"Could not provision openai_compatible from ProviderConfig: {e}"
        )

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

    NOTE: This function is deprecated for request-time use because it can leave
    stale env vars after key deletion. Keys should only be provisioned at startup
    or via provision_provider_keys() for specific providers.

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


# Alternative function that uses fresh DB values instead of modifying os.environ
async def get_provider_config(provider: str) -> Optional[dict]:
    """
    Get provider configuration directly from database.

    This is a cleaner alternative to provision_provider_keys() that doesn't
    modify global state. Returns the configuration values without setting env vars.

    Args:
        provider: Provider name

    Returns:
        Dict with configuration values, or None if not configured
    """
    provider_lower = provider.lower()

    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config(provider_lower)

        if not default_cred:
            return None

        config = {}

        # Extract api_key (handle SecretStr)
        if default_cred.api_key:
            config["api_key"] = default_cred.api_key.get_secret_value()

        # Add all other fields if present
        if default_cred.base_url:
            config["base_url"] = default_cred.base_url
        if default_cred.model:
            config["model"] = default_cred.model
        if default_cred.api_version:
            config["api_version"] = default_cred.api_version
        if default_cred.endpoint:
            config["endpoint"] = default_cred.endpoint
        if default_cred.endpoint_llm:
            config["endpoint_llm"] = default_cred.endpoint_llm
        if default_cred.endpoint_embedding:
            config["endpoint_embedding"] = default_cred.endpoint_embedding
        if default_cred.endpoint_stt:
            config["endpoint_stt"] = default_cred.endpoint_stt
        if default_cred.endpoint_tts:
            config["endpoint_tts"] = default_cred.endpoint_tts
        if default_cred.project:
            config["project"] = default_cred.project
        if default_cred.location:
            config["location"] = default_cred.location
        if default_cred.credentials_path:
            config["credentials_path"] = default_cred.credentials_path

        return config if config else None

    except Exception as e:
        logger.debug(f"Could not load provider config from database for {provider}: {e}")

    return None
