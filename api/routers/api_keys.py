"""
API Key Management Router

Provides endpoints for managing API keys for AI providers.
Keys are stored in the database via ProviderConfig singleton.
NEVER returns actual API key values - only status information.
"""

import ipaddress
import os
import socket
import uuid
from datetime import datetime
from typing import Dict, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import SecretStr

from api.models import (
    ApiKeyStatusResponse,
    MigrationResult,
    SetApiKeyRequest,
    TestConnectionResponse,
)
from open_notebook.ai.connection_tester import test_provider_connection
from open_notebook.domain.provider_config import ProviderConfig, ProviderCredential

router = APIRouter()


def _validate_url(url: str, provider: str) -> None:
    """
    Validate URL format for API endpoints.

    This is a self-hosted application, so we allow:
    - Private IPs (10.x, 172.16-31.x, 192.168.x) for self-hosted services
    - Localhost for local services (Ollama, LM Studio, etc.)

    We only block:
    - Invalid schemes (must be http or https)
    - Malformed URLs
    - Link-local addresses (169.254.x.x) - used for cloud metadata endpoints
    - Hostnames that resolve to link-local addresses

    Args:
        url: The URL to validate
        provider: The provider name (for logging/context)

    Raises:
        HTTPException: If the URL is invalid
    """
    if not url or not url.strip():
        return  # Empty URLs handled elsewhere

    try:
        parsed = urlparse(url.strip())

        # Validate scheme - only http/https allowed
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL scheme: '{parsed.scheme}'. Only http and https are allowed.",
            )

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(
                status_code=400,
                detail="Invalid URL: hostname could not be determined.",
            )

        # Try to parse as IP address to check for dangerous addresses
        try:
            ip = ipaddress.ip_address(hostname)

            # Block link-local addresses (169.254.x.x) - used for cloud metadata
            # These are dangerous as they can expose cloud instance credentials
            if ip.is_link_local:
                raise HTTPException(
                    status_code=400,
                    detail="Link-local addresses (169.254.x.x) are not allowed for security reasons. "
                    "These addresses are used for cloud metadata endpoints.",
                )

        except ValueError:
            # Not an IP address, it's a hostname - need to resolve and check
            try:
                # Resolve hostname to IP address
                resolved_ips = socket.getaddrinfo(hostname, None)
                for family, _, _, _, sockaddr in resolved_ips:
                    ip_addr = sockaddr[0]
                    try:
                        parsed_ip = ipaddress.ip_address(ip_addr)
                        if parsed_ip.is_link_local:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Hostname '{hostname}' resolves to a link-local address (169.254.x.x) which is not allowed for security reasons. "
                                "These addresses are used for cloud metadata endpoints.",
                            )
                    except ValueError:
                        # Skip non-IP addresses (e.g., IPv6 zones)
                        continue
            except socket.gaierror:
                # Could not resolve hostname - reject it for security
                raise HTTPException(
                    status_code=400,
                    detail=f"Hostname '{hostname}' could not be resolved. For security reasons, only valid resolvable hostnames are allowed.",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format. Check server logs for details.",
        )


# Provider to environment variable mapping
PROVIDER_ENV_MAPPING: Dict[str, list[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "voyage": ["VOYAGE_API_KEY"],
    "elevenlabs": ["ELEVENLABS_API_KEY"],
    "ollama": ["OLLAMA_API_BASE"],
    "vertex": ["VERTEX_PROJECT", "VERTEX_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS"],
    "azure": [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
    ],
    "openai_compatible": ["OPENAI_COMPATIBLE_BASE_URL", "OPENAI_COMPATIBLE_API_KEY"],
}

# Valid provider names (for validation)
VALID_PROVIDERS = set(PROVIDER_ENV_MAPPING.keys())


def _check_env_configured(provider: str) -> bool:
    """Check if a provider is configured via environment variables.
    
    Env vars must be set AND non-empty to count as configured.
    """
    env_vars = PROVIDER_ENV_MAPPING.get(provider, [])
    if not env_vars:
        return False

    def _env_has_value(var: str) -> bool:
        """Check if env var is set and non-empty."""
        value = os.environ.get(var)
        return value is not None and value.strip() != ""

    # For providers that need multiple vars (vertex, azure), check if all required are set
    if provider == "vertex":
        return all(_env_has_value(var) for var in env_vars)
    elif provider == "azure":
        # Azure needs at least the key, endpoint, and version
        return (
            _env_has_value("AZURE_OPENAI_API_KEY")
            and _env_has_value("AZURE_OPENAI_ENDPOINT")
            and _env_has_value("AZURE_OPENAI_API_VERSION")
        )
    elif provider == "google":
        # Google can use either GOOGLE_API_KEY or GEMINI_API_KEY
        return any(_env_has_value(var) for var in env_vars)
    elif provider == "openai_compatible":
        # OpenAI-compatible needs at least a base URL
        return _env_has_value("OPENAI_COMPATIBLE_BASE_URL")
    else:
        # Simple providers just need their single env var
        return _env_has_value(env_vars[0])


async def _check_db_configured(provider: str) -> bool:
    """
    Check if a provider is configured in ProviderConfig.

    Returns:
        True if provider has at least one valid configuration, False otherwise.
    """
    try:
        provider_config = await ProviderConfig.get_instance()
        default_cred = provider_config.get_default_config(provider)
        return default_cred is not None
    except Exception:
        pass

    return False


def _get_source(
    provider: str, env_configured: bool, db_configured: bool
) -> Literal["database", "environment", "none"]:
    """Determine the configuration source for a provider."""
    if db_configured:
        return "database"
    elif env_configured:
        return "environment"
    else:
        return "none"


@router.get("/api-keys/status", response_model=ApiKeyStatusResponse)
async def get_api_keys_status():
    """
    Get the configuration status of all API providers.

    Returns which providers are configured and their configuration source
    (database, environment, or none). NEVER returns actual key values.
    """
    try:
        configured: Dict[str, bool] = {}
        source: Dict[str, Literal["database", "environment", "none"]] = {}

        for provider in VALID_PROVIDERS:
            env_configured = _check_env_configured(provider)
            db_configured = await _check_db_configured(provider)

            configured[provider] = db_configured or env_configured
            source[provider] = _get_source(provider, env_configured, db_configured)

        return ApiKeyStatusResponse(configured=configured, source=source)
    except Exception as e:
        logger.error(f"Error fetching API key status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching API key status: {str(e)}"
        )


@router.get("/api-keys/env-status")
async def get_env_status():
    """
    Check what's configured via environment variables.

    Used by the migration UI to show which providers can be migrated
    from environment variables to database storage.
    """
    try:
        env_status: Dict[str, bool] = {}
        for provider in VALID_PROVIDERS:
            env_status[provider] = _check_env_configured(provider)

        return env_status
    except Exception as e:
        logger.error(f"Error checking environment status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error checking environment status: {str(e)}"
        )


@router.post("/api-keys/{provider}")
async def set_api_key(provider: str, request: SetApiKeyRequest):
    """
    Set API key(s) for a provider.

    Body varies by provider:
    - Simple providers: {"api_key": "sk-..."}
    - Azure: {"api_key": "...", "endpoint": "...", "api_version": "..."}
    - OpenAI-Compatible: {"api_key": "...", "base_url": "...", "service_type": "llm|embedding|stt|tts"}
    - Ollama: {"base_url": "http://localhost:11434"}
    - Vertex: Pass via separate endpoint or use environment variables
    """
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Valid providers: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    try:
        provider_config = await ProviderConfig.get_instance()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate config ID
        config_id = f"{provider}:{uuid.uuid4().hex[:8]}"

        # Build credential based on provider type
        cred = ProviderCredential(
            id=config_id,
            name="Default",
            provider=provider,
            is_default=True,
            api_key=SecretStr(request.api_key) if request.api_key else None,
            base_url=request.base_url,
            api_version=request.api_version,
            endpoint=request.endpoint,
            endpoint_llm=request.endpoint_llm,
            endpoint_embedding=request.endpoint_embedding,
            endpoint_stt=request.endpoint_stt,
            endpoint_tts=request.endpoint_tts,
            project=request.vertex_project,
            location=request.vertex_location,
            credentials_path=request.vertex_credentials_path,
            created=now,
            updated=now,
        )

        # Validate URLs if provided
        if request.base_url:
            _validate_url(request.base_url, provider)
        if request.endpoint:
            _validate_url(request.endpoint, provider)
        if request.endpoint_llm:
            _validate_url(request.endpoint_llm, provider)
        if request.endpoint_embedding:
            _validate_url(request.endpoint_embedding, provider)
        if request.endpoint_stt:
            _validate_url(request.endpoint_stt, provider)
        if request.endpoint_tts:
            _validate_url(request.endpoint_tts, provider)

        # Unset other defaults for this provider
        existing = provider_config.credentials.get(provider, [])
        for existing_cred in existing:
            existing_cred.is_default = False

        # Add new credential
        provider_config.add_config(provider, cred)

        # Save to ProviderConfig
        await provider_config.save()

        return {"message": f"API key for {provider} saved successfully"}

    except Exception as e:
        logger.error(f"Error setting API key for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error setting API key: {str(e)}"
        )


@router.delete("/api-keys/{provider}")
async def delete_api_key(provider: str, service_type: str | None = None):
    """
    Remove configuration for a provider.

    For openai_compatible, optionally specify service_type to delete
    only that service's configuration (llm, embedding, stt, tts).
    Without service_type, deletes all openai_compatible configurations.
    """
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Valid providers: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    try:
        provider_config = await ProviderConfig.get_instance()
        credentials = provider_config.credentials.get(provider, [])

        if not credentials:
            raise HTTPException(status_code=404, detail=f"No configurations found for {provider}")

        # Get the default config ID to delete
        default_cred = provider_config.get_default_config(provider)
        if default_cred:
            deleted = provider_config.delete_config(provider, default_cred.id)
            if deleted:
                await provider_config.save()
                return {"message": f"Configuration for {provider} deleted successfully"}

        raise HTTPException(status_code=404, detail=f"No default configuration found for {provider}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting API key: {str(e)}"
        )


@router.post("/api-keys/{provider}/test", response_model=TestConnectionResponse)
async def test_provider(provider: str):
    """
    Test connection for a provider using configured API key.

    Makes a minimal API call to verify the API key is valid.
    Uses the cheapest/smallest model available for each provider.

    Supports两种格式：
    - /api-keys/{provider}/test - 测试默认配置
    - /api-keys/{provider}:{configId}/test - 测试特定配置

    Returns success status and a descriptive message.
    """
    # Parse provider and optional config_id from path
    # Format: "deepseek" or "deepseek:abc12345"
    if ":" in provider:
        provider_name, config_id = provider.split(":", 1)
    else:
        provider_name = provider
        config_id = None

    if provider_name not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider_name}. Valid providers: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    try:
        success, message = await test_provider_connection(provider_name, config_id=config_id)

        return TestConnectionResponse(
            provider=provider,
            success=success,
            message=message,
        )

    except Exception as e:
        logger.error(f"Error testing connection for {provider}: {str(e)}")
        return TestConnectionResponse(
            provider=provider,
            success=False,
            message=f"Test failed: {str(e)[:100]}",
        )


@router.post("/api-keys/migrate", response_model=MigrationResult)
async def migrate_from_env(force: bool = False):
    """
    Migrate API keys from environment variables to database.

    By default, only migrates providers that have environment variables set
    but don't have database configuration yet. This preserves any existing
    database configurations.

    Set force=True to overwrite existing database configurations with
    environment variable values.
    """
    try:
        provider_config = await ProviderConfig.get_instance()
        migrated: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for provider in VALID_PROVIDERS:
            env_configured = _check_env_configured(provider)
            db_configured = await _check_db_configured(provider)

            # Skip if not in env
            if not env_configured:
                continue
            # Skip if already in DB (unless force=True)
            if db_configured and not force:
                skipped.append(provider)
                continue

            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                config_id = f"{provider}:{uuid.uuid4().hex[:8]}"

                # Build credential from environment
                cred = ProviderCredential(
                    id=config_id,
                    name="Default (Migrated)",
                    provider=provider,
                    is_default=True,
                    created=now,
                    updated=now,
                )

                # Migrate based on provider type
                if provider == "openai":
                    cred.api_key = SecretStr(os.environ["OPENAI_API_KEY"])
                elif provider == "anthropic":
                    cred.api_key = SecretStr(os.environ["ANTHROPIC_API_KEY"])
                elif provider == "google":
                    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
                    if key:
                        cred.api_key = SecretStr(key)
                elif provider == "groq":
                    cred.api_key = SecretStr(os.environ["GROQ_API_KEY"])
                elif provider == "mistral":
                    cred.api_key = SecretStr(os.environ["MISTRAL_API_KEY"])
                elif provider == "deepseek":
                    cred.api_key = SecretStr(os.environ["DEEPSEEK_API_KEY"])
                elif provider == "xai":
                    cred.api_key = SecretStr(os.environ["XAI_API_KEY"])
                elif provider == "openrouter":
                    cred.api_key = SecretStr(os.environ["OPENROUTER_API_KEY"])
                elif provider == "voyage":
                    cred.api_key = SecretStr(os.environ["VOYAGE_API_KEY"])
                elif provider == "elevenlabs":
                    cred.api_key = SecretStr(os.environ["ELEVENLABS_API_KEY"])
                elif provider == "ollama":
                    base_url = os.environ["OLLAMA_API_BASE"]
                    _validate_url(base_url, provider)
                    cred.base_url = base_url
                elif provider == "vertex":
                    cred.project = os.environ["VERTEX_PROJECT"]
                    cred.location = os.environ["VERTEX_LOCATION"]
                    cred.credentials_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
                elif provider == "azure":
                    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
                    _validate_url(endpoint, provider)
                    cred.api_key = SecretStr(os.environ["AZURE_OPENAI_API_KEY"])
                    cred.endpoint = endpoint
                    cred.api_version = os.environ["AZURE_OPENAI_API_VERSION"]
                elif provider == "openai_compatible":
                    base_url = os.environ.get("OPENAI_COMPATIBLE_BASE_URL")
                    if base_url:
                        _validate_url(base_url, provider)
                        cred.base_url = base_url
                    if os.environ.get("OPENAI_COMPATIBLE_API_KEY"):
                        cred.api_key = SecretStr(os.environ["OPENAI_COMPATIBLE_API_KEY"])

                # Unset other defaults and add new
                existing = provider_config.credentials.get(provider, [])
                for existing_cred in existing:
                    existing_cred.is_default = False

                provider_config.add_config(provider, cred)
                migrated.append(provider)

            except Exception as e:
                errors.append(f"{provider}: {str(e)}")

        # Save all migrated configs
        if migrated:
            await provider_config.save()

        return MigrationResult(
            message=f"Migration complete. Migrated {len(migrated)} providers.",
            migrated=migrated,
            skipped=skipped,
            errors=errors,
        )

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
