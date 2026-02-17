"""
Credentials Service

Business logic for managing AI provider credentials.
Extracted from the credentials router to follow the service layer pattern.

All functions raise ValueError for business errors (router converts to HTTPException).
"""

import ipaddress
import os
import socket
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from loguru import logger
from pydantic import SecretStr

from api.models import CredentialResponse
from open_notebook.domain.credential import Credential
from open_notebook.utils.encryption import get_secret_from_env

# =============================================================================
# Constants
# =============================================================================

# Provider environment variable configuration.
# - "required": ALL listed env vars must be set for the provider to be considered configured.
# - "required_any": at least ONE of the listed env vars must be set.
# - "optional": additional env vars used during migration but not required.
PROVIDER_ENV_CONFIG: Dict[str, dict] = {
    "openai": {"required": ["OPENAI_API_KEY"]},
    "anthropic": {"required": ["ANTHROPIC_API_KEY"]},
    "google": {"required_any": ["GOOGLE_API_KEY", "GEMINI_API_KEY"]},
    "groq": {"required": ["GROQ_API_KEY"]},
    "mistral": {"required": ["MISTRAL_API_KEY"]},
    "deepseek": {"required": ["DEEPSEEK_API_KEY"]},
    "xai": {"required": ["XAI_API_KEY"]},
    "openrouter": {"required": ["OPENROUTER_API_KEY"]},
    "voyage": {"required": ["VOYAGE_API_KEY"]},
    "elevenlabs": {"required": ["ELEVENLABS_API_KEY"]},
    "ollama": {"required": ["OLLAMA_API_BASE"]},
    "vertex": {
        "required": ["VERTEX_PROJECT", "VERTEX_LOCATION"],
        "optional": ["GOOGLE_APPLICATION_CREDENTIALS"],
    },
    "azure": {
        "required": ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION"],
        "optional": [
            "AZURE_OPENAI_ENDPOINT_LLM",
            "AZURE_OPENAI_ENDPOINT_EMBEDDING",
            "AZURE_OPENAI_ENDPOINT_STT",
            "AZURE_OPENAI_ENDPOINT_TTS",
        ],
    },
    "openai_compatible": {
        "required_any": ["OPENAI_COMPATIBLE_BASE_URL", "OPENAI_COMPATIBLE_API_KEY"],
    },
}

PROVIDER_MODALITIES: Dict[str, List[str]] = {
    "openai": ["language", "embedding", "speech_to_text", "text_to_speech"],
    "anthropic": ["language"],
    "google": ["language", "embedding"],
    "groq": ["language", "speech_to_text"],
    "mistral": ["language", "embedding"],
    "deepseek": ["language"],
    "xai": ["language"],
    "openrouter": ["language"],
    "voyage": ["embedding"],
    "elevenlabs": ["text_to_speech"],
    "ollama": ["language", "embedding"],
    "vertex": ["language", "embedding"],
    "azure": ["language", "embedding", "speech_to_text", "text_to_speech"],
    "openai_compatible": ["language", "embedding", "speech_to_text", "text_to_speech"],
}


# =============================================================================
# URL Validation (SSRF protection)
# =============================================================================


def validate_url(url: str, provider: str) -> None:
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
        ValueError: If the URL is invalid
    """
    if not url or not url.strip():
        return  # Empty URLs handled elsewhere

    try:
        parsed = urlparse(url.strip())

        # Validate scheme - only http/https allowed
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme: '{parsed.scheme}'. Only http and https are allowed."
            )

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: hostname could not be determined.")

        # Try to parse as IP address to check for dangerous addresses
        try:
            ip = ipaddress.ip_address(hostname)

            # Block link-local addresses (169.254.x.x) - used for cloud metadata
            # These are dangerous as they can expose cloud instance credentials
            if ip.is_link_local:
                raise ValueError(
                    "Link-local addresses (169.254.x.x) are not allowed for security reasons. "
                    "These addresses are used for cloud metadata endpoints."
                )

            # Block IPv4-mapped IPv6 addresses pointing to link-local
            # e.g. ::ffff:169.254.169.254 bypasses IPv6 is_link_local check
            if hasattr(ip, "ipv4_mapped") and ip.ipv4_mapped and ip.ipv4_mapped.is_link_local:
                raise ValueError(
                    "Link-local addresses (169.254.x.x) are not allowed for security reasons. "
                    "These addresses are used for cloud metadata endpoints."
                )

        except ValueError as ve:
            # Re-raise our own ValueErrors
            if "Link-local" in str(ve) or "Invalid URL" in str(ve):
                raise
            # Not an IP address, it's a hostname - need to resolve and check
            try:
                # Resolve hostname to IP address
                resolved_ips = socket.getaddrinfo(hostname, None)
                for family, _, _, _, sockaddr in resolved_ips:
                    ip_addr = sockaddr[0]
                    try:
                        parsed_ip = ipaddress.ip_address(ip_addr)
                        if parsed_ip.is_link_local:
                            raise ValueError(
                                f"Hostname '{hostname}' resolves to a link-local address (169.254.x.x) which is not allowed for security reasons. "
                                "These addresses are used for cloud metadata endpoints."
                            )
                        # Block IPv4-mapped IPv6 addresses pointing to link-local
                        if (
                            hasattr(parsed_ip, "ipv4_mapped")
                            and parsed_ip.ipv4_mapped
                            and parsed_ip.ipv4_mapped.is_link_local
                        ):
                            raise ValueError(
                                f"Hostname '{hostname}' resolves to a link-local address (169.254.x.x) which is not allowed for security reasons. "
                                "These addresses are used for cloud metadata endpoints."
                            )
                    except ValueError as inner_ve:
                        if "link-local" in str(inner_ve).lower() or "Link-local" in str(inner_ve):
                            raise
                        # Skip non-IP addresses (e.g., IPv6 zones)
                        continue
            except socket.gaierror:
                # Could not resolve hostname - allow it since the URL may be
                # valid in the deployment environment (e.g., Azure endpoints,
                # internal DNS names). We only block link-local addresses.
                pass

    except ValueError:
        raise
    except Exception:
        raise ValueError("Invalid URL format. Check server logs for details.")


# =============================================================================
# Helpers
# =============================================================================


def require_encryption_key() -> None:
    """Raise ValueError if encryption key is not configured."""
    if not get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"):
        raise ValueError(
            "Encryption key not configured. "
            "Set OPEN_NOTEBOOK_ENCRYPTION_KEY to enable storing API keys."
        )


def credential_to_response(cred: Credential, model_count: int = 0) -> CredentialResponse:
    """Convert a Credential domain object to API response."""
    return CredentialResponse(
        id=cred.id or "",
        name=cred.name,
        provider=cred.provider,
        modalities=cred.modalities,
        base_url=cred.base_url,
        endpoint=cred.endpoint,
        api_version=cred.api_version,
        endpoint_llm=cred.endpoint_llm,
        endpoint_embedding=cred.endpoint_embedding,
        endpoint_stt=cred.endpoint_stt,
        endpoint_tts=cred.endpoint_tts,
        project=cred.project,
        location=cred.location,
        credentials_path=cred.credentials_path,
        has_api_key=cred.api_key is not None,
        created=str(cred.created) if cred.created else "",
        updated=str(cred.updated) if cred.updated else "",
        model_count=model_count,
    )


def check_env_configured(provider: str) -> bool:
    """Check if a provider has sufficient env vars configured for migration."""
    config = PROVIDER_ENV_CONFIG.get(provider)
    if not config:
        return False

    if "required_any" in config:
        return any(bool(os.environ.get(v, "").strip()) for v in config["required_any"])
    elif "required" in config:
        return all(bool(os.environ.get(v, "").strip()) for v in config["required"])
    return False


def get_default_modalities(provider: str) -> List[str]:
    """Get default modalities for a provider."""
    return PROVIDER_MODALITIES.get(provider.lower(), ["language"])


def create_credential_from_env(provider: str) -> Credential:
    """Create a Credential from environment variables for a given provider."""
    modalities = get_default_modalities(provider)
    name = "Default (Migrated from env)"

    if provider == "ollama":
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            base_url=os.environ.get("OLLAMA_API_BASE"),
        )
    elif provider == "vertex":
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            project=os.environ.get("VERTEX_PROJECT"),
            location=os.environ.get("VERTEX_LOCATION"),
            credentials_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        )
    elif provider == "azure":
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"]),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
            endpoint_llm=os.environ.get("AZURE_OPENAI_ENDPOINT_LLM"),
            endpoint_embedding=os.environ.get("AZURE_OPENAI_ENDPOINT_EMBEDDING"),
            endpoint_stt=os.environ.get("AZURE_OPENAI_ENDPOINT_STT"),
            endpoint_tts=os.environ.get("AZURE_OPENAI_ENDPOINT_TTS"),
        )
    elif provider == "openai_compatible":
        api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            api_key=SecretStr(api_key) if api_key else None,
            base_url=os.environ.get("OPENAI_COMPATIBLE_BASE_URL"),
        )
    elif provider == "google":
        # Support both GOOGLE_API_KEY and GEMINI_API_KEY (fallback)
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            api_key=SecretStr(api_key) if api_key else None,
        )
    else:
        # Simple API key providers
        config = PROVIDER_ENV_CONFIG.get(provider, {})
        required = config.get("required", [])
        env_var = required[0] if required else None
        api_key = os.environ.get(env_var) if env_var else None
        return Credential(
            name=name,
            provider=provider,
            modalities=modalities,
            api_key=SecretStr(api_key) if api_key else None,
        )


# =============================================================================
# Service Functions
# =============================================================================


async def get_provider_status() -> dict:
    """
    Get configuration status: encryption key status, and per-provider
    configured/source information.
    """
    encryption_configured = bool(get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY"))

    configured: Dict[str, bool] = {}
    source: Dict[str, str] = {}

    for provider in PROVIDER_ENV_CONFIG:
        env_configured = check_env_configured(provider)
        try:
            db_credentials = await Credential.get_by_provider(provider)
            db_configured = len(db_credentials) > 0
        except Exception:
            db_configured = False

        configured[provider] = db_configured or env_configured

        if db_configured:
            source[provider] = "database"
        elif env_configured:
            source[provider] = "environment"
        else:
            source[provider] = "none"

    return {
        "configured": configured,
        "source": source,
        "encryption_configured": encryption_configured,
    }


async def get_env_status() -> Dict[str, bool]:
    """Check what's configured via environment variables."""
    env_status: Dict[str, bool] = {}
    for provider in PROVIDER_ENV_CONFIG:
        env_status[provider] = check_env_configured(provider)
    return env_status


async def test_credential(credential_id: str) -> dict:
    """
    Test connection using a credential's configuration.

    Returns dict with provider, success, message keys.
    """
    provider = "unknown"
    try:
        cred = await Credential.get(credential_id)
        config = cred.to_esperanto_config()

        from open_notebook.ai.connection_tester import (
            _test_azure_connection,
            _test_ollama_connection,
            _test_openai_compatible_connection,
        )

        provider = cred.provider.lower()

        # Handle special providers
        if provider == "ollama":
            base_url = config.get("base_url", "http://localhost:11434")
            success, message = await _test_ollama_connection(base_url)
            return {"provider": provider, "success": success, "message": message}

        if provider == "openai_compatible":
            base_url = config.get("base_url")
            api_key = config.get("api_key")
            if not base_url:
                return {
                    "provider": provider,
                    "success": False,
                    "message": "No base URL configured",
                }
            success, message = await _test_openai_compatible_connection(
                base_url, api_key
            )
            return {"provider": provider, "success": success, "message": message}

        if provider == "azure":
            success, message = await _test_azure_connection(
                endpoint=config.get("endpoint"),
                api_key=config.get("api_key"),
                api_version=config.get("api_version"),
            )
            return {"provider": provider, "success": success, "message": message}

        # Standard provider: use Esperanto to create and test
        from esperanto.factory import AIFactory

        from open_notebook.ai.connection_tester import TEST_MODELS

        if provider not in TEST_MODELS:
            return {
                "provider": provider,
                "success": False,
                "message": f"Unknown provider: {provider}",
            }

        test_model, test_type = TEST_MODELS[provider]
        if not test_model:
            return {
                "provider": provider,
                "success": False,
                "message": f"No test model configured for {provider}",
            }

        if test_type == "language":
            model = AIFactory.create_language(
                model_name=test_model, provider=provider, config=config
            )
            lc_model = model.to_langchain()
            await lc_model.ainvoke("Hi")
            return {"provider": provider, "success": True, "message": "Connection successful"}

        elif test_type == "embedding":
            model = AIFactory.create_embedding(
                model_name=test_model, provider=provider, config=config
            )
            await model.aembed(["test"])
            return {"provider": provider, "success": True, "message": "Connection successful"}

        elif test_type == "text_to_speech":
            AIFactory.create_text_to_speech(model_name=test_model, provider=provider, config=config)
            return {
                "provider": provider,
                "success": True,
                "message": "Connection successful (key format valid)",
            }

        return {
            "provider": provider,
            "success": False,
            "message": f"Unsupported test type: {test_type}",
        }

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return {"provider": provider, "success": False, "message": "Invalid API key"}
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            return {"provider": provider, "success": False, "message": "API key lacks required permissions"}
        elif "rate" in error_msg.lower() and "limit" in error_msg.lower():
            return {"provider": provider, "success": True, "message": "Rate limited - but connection works"}
        elif "not found" in error_msg.lower() and "model" in error_msg.lower():
            return {"provider": provider, "success": True, "message": "API key valid (test model not available)"}
        else:
            logger.debug(f"Test connection error for credential {credential_id}: {e}")
            truncated = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
            return {"provider": provider, "success": False, "message": f"Error: {truncated}"}


async def discover_with_config(provider: str, config: dict) -> List[dict]:
    """
    Discover models using explicit config instead of env vars.

    Returns model names only — no type classification.
    The user chooses the model type when registering.
    """
    api_key = config.get("api_key")
    base_url = config.get("base_url")

    # Static model lists for providers without a listing API
    STATIC_MODELS: Dict[str, List[str]] = {
        "anthropic": [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "voyage": [
            "voyage-3", "voyage-3-lite", "voyage-code-3",
            "voyage-finance-2", "voyage-law-2", "voyage-multilingual-2",
        ],
        "elevenlabs": [
            "eleven_multilingual_v2", "eleven_turbo_v2_5",
            "eleven_turbo_v2", "eleven_monolingual_v1",
        ],
    }

    if provider in STATIC_MODELS:
        if not api_key and provider != "ollama":
            return []
        return [
            {"name": m, "provider": provider}
            for m in STATIC_MODELS[provider]
        ]

    # API-based discovery URLs (OpenAI-style /models endpoints)
    url_map = {
        "openai": "https://api.openai.com/v1/models",
        "groq": "https://api.groq.com/openai/v1/models",
        "mistral": "https://api.mistral.ai/v1/models",
        "deepseek": "https://api.deepseek.com/models",
        "xai": "https://api.x.ai/v1/models",
        "openrouter": "https://openrouter.ai/api/v1/models",
    }

    if provider == "ollama":
        ollama_url = base_url or "http://localhost:11434"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return [
                    {"name": m.get("name", ""), "provider": "ollama"}
                    for m in data.get("models", [])
                    if m.get("name")
                ]
        except Exception as e:
            logger.warning(f"Failed to discover Ollama models: {e}")
            return []

    if provider == "openai_compatible":
        if not base_url:
            return []
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/models", headers=headers, timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {"name": m.get("id", ""), "provider": "openai_compatible"}
                    for m in data.get("data", [])
                    if m.get("id")
                ]
        except Exception as e:
            logger.warning(f"Failed to discover openai_compatible models: {e}")
            return []

    if provider == "azure":
        endpoint = config.get("endpoint")
        api_version = config.get("api_version", "2024-06-01")
        if not endpoint or not api_key:
            return []
        try:
            url = f"{endpoint.rstrip('/')}/openai/models?api-version={api_version}"
            headers = {"api-key": api_key}
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return [
                    {"name": m.get("id", ""), "provider": "azure"}
                    for m in data.get("data", [])
                    if m.get("id")
                ]
        except Exception as e:
            logger.warning(f"Failed to discover Azure models: {e}")
            return []

    if provider == "vertex":
        # Vertex AI requires service-account OAuth2 for model listing.
        # Return a curated static list of well-known Vertex models instead.
        VERTEX_MODELS = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "text-embedding-005",
        ]
        return [{"name": m, "provider": "vertex"} for m in VERTEX_MODELS]

    if provider == "google":
        try:
            headers = {"X-Goog-Api-Key": api_key} if api_key else {}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://generativelanguage.googleapis.com/v1/models",
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "name": model.get("name", "").replace("models/", ""),
                        "provider": "google",
                        "description": model.get("displayName"),
                    }
                    for model in data.get("models", [])
                    if model.get("name")
                ]
        except Exception as e:
            logger.warning(f"Failed to discover Google models: {e}")
            return []

    # Standard OpenAI-style API discovery
    discovery_url = url_map.get(provider)
    if not discovery_url or not api_key:
        return []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                discovery_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "name": m.get("id", ""),
                    "provider": provider,
                    "description": m.get("name"),
                }
                for m in data.get("data", [])
                if m.get("id")
            ]
    except Exception as e:
        logger.warning(f"Failed to discover {provider} models: {e}")
        return []


async def register_models(credential_id: str, models_data: list) -> dict:
    """
    Register discovered models and link them to a credential.

    Args:
        credential_id: The credential ID to link models to
        models_data: List of dicts with name, provider, model_type

    Returns:
        dict with created and existing counts
    """
    cred = await Credential.get(credential_id)

    from open_notebook.ai.models import Model
    from open_notebook.database.repository import repo_query

    # Batch fetch existing models for this provider
    existing_models = await repo_query(
        "SELECT string::lowercase(name) as name, string::lowercase(type) as type FROM model "
        "WHERE string::lowercase(provider) = $provider",
        {"provider": cred.provider.lower()},
    )
    existing_keys = {(m["name"], m["type"]) for m in existing_models}

    created = 0
    existing = 0

    for model_data in models_data:
        key = (model_data.name.lower(), model_data.model_type.lower())
        if key in existing_keys:
            existing += 1
            continue

        new_model = Model(
            name=model_data.name,
            provider=model_data.provider or cred.provider,
            type=model_data.model_type,
            credential=cred.id,
        )
        await new_model.save()
        created += 1

    return {"created": created, "existing": existing}


async def migrate_from_provider_config() -> dict:
    """
    Migrate existing ProviderConfig data to individual credential records.

    Returns dict with message, migrated, skipped, errors.
    """
    logger.info("=== Starting ProviderConfig migration ===")

    require_encryption_key()
    logger.info("Encryption key verified")

    from open_notebook.domain.provider_config import ProviderConfig

    config = await ProviderConfig.get_instance()
    logger.info(
        f"Found ProviderConfig with {len(config.credentials)} provider(s): "
        f"{', '.join(config.credentials.keys())}"
    )

    migrated = []
    skipped = []
    errors = []

    for provider, credentials_list in config.credentials.items():
        for old_cred in credentials_list:
            try:
                # Check if a credential already exists for this provider with same name
                existing = await Credential.get_by_provider(provider)
                names = [c.name for c in existing]
                if old_cred.name in names:
                    logger.info(
                        f"[{provider}/{old_cred.name}] Already exists in DB, skipping"
                    )
                    skipped.append(f"{provider}/{old_cred.name}")
                    continue

                # Determine modalities from the provider type
                modalities = get_default_modalities(provider)

                logger.info(f"[{provider}/{old_cred.name}] Creating credential")
                new_cred = Credential(
                    name=old_cred.name,
                    provider=provider,
                    modalities=modalities,
                    api_key=old_cred.api_key,
                    base_url=old_cred.base_url,
                    endpoint=old_cred.endpoint,
                    api_version=old_cred.api_version,
                    endpoint_llm=old_cred.endpoint_llm,
                    endpoint_embedding=old_cred.endpoint_embedding,
                    endpoint_stt=old_cred.endpoint_stt,
                    endpoint_tts=old_cred.endpoint_tts,
                    project=old_cred.project,
                    location=old_cred.location,
                    credentials_path=old_cred.credentials_path,
                )
                await new_cred.save()
                logger.info(
                    f"[{provider}/{old_cred.name}] Credential saved (id={new_cred.id})"
                )

                # Link existing models for this provider to the new credential
                from open_notebook.ai.models import Model
                from open_notebook.database.repository import repo_query

                provider_models = await repo_query(
                    "SELECT * FROM model WHERE string::lowercase(provider) = $provider AND credential IS NONE",
                    {"provider": provider.lower()},
                )
                if provider_models:
                    logger.info(
                        f"[{provider}/{old_cred.name}] Linking {len(provider_models)} "
                        f"unassigned model(s)"
                    )
                    for model_data in provider_models:
                        model = Model(**model_data)
                        model.credential = new_cred.id
                        await model.save()

                migrated.append(f"{provider}/{old_cred.name}")

            except Exception as e:
                logger.error(
                    f"[{provider}/{old_cred.name}] Migration FAILED: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                errors.append(f"{provider}/{old_cred.name}: {e}")

    logger.info(
        f"=== ProviderConfig migration complete === "
        f"migrated={len(migrated)} skipped={len(skipped)} errors={len(errors)}"
    )
    if migrated:
        logger.info(f"  Migrated: {', '.join(migrated)}")
    if skipped:
        logger.info(f"  Skipped: {', '.join(skipped)}")
    if errors:
        logger.error(f"  Errors: {'; '.join(errors)}")

    return {
        "message": f"Migration complete. Migrated {len(migrated)} credentials.",
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors,
    }


async def migrate_from_env() -> dict:
    """
    Migrate API keys from environment variables to credential records.

    Returns dict with message, migrated, skipped, not_configured, errors.
    """
    logger.info("=== Starting environment variable migration ===")
    logger.info(
        f"Checking {len(PROVIDER_ENV_CONFIG)} providers: "
        f"{', '.join(PROVIDER_ENV_CONFIG.keys())}"
    )

    require_encryption_key()
    logger.info("Encryption key verified")

    from open_notebook.ai.models import Model
    from open_notebook.database.repository import repo_query

    migrated = []
    skipped = []
    not_configured = []
    errors = []

    for provider in PROVIDER_ENV_CONFIG:
        try:
            if not check_env_configured(provider):
                logger.debug(f"[{provider}] No env vars configured, skipping")
                not_configured.append(provider)
                continue

            logger.info(f"[{provider}] Env vars detected, checking for existing credentials")

            existing = await Credential.get_by_provider(provider)
            if existing:
                logger.info(
                    f"[{provider}] Already has {len(existing)} credential(s) in DB, skipping"
                )
                skipped.append(provider)
                continue

            logger.info(f"[{provider}] Creating credential from env vars")
            cred = create_credential_from_env(provider)
            await cred.save()
            logger.info(f"[{provider}] Credential saved successfully (id={cred.id})")

            # Link unassigned models to this credential
            provider_models = await repo_query(
                "SELECT * FROM model WHERE string::lowercase(provider) = $provider AND credential IS NONE",
                {"provider": provider.lower()},
            )
            if provider_models:
                logger.info(
                    f"[{provider}] Linking {len(provider_models)} unassigned model(s) "
                    f"to credential {cred.id}"
                )
                for model_data in provider_models:
                    model = Model(**model_data)
                    model.credential = cred.id
                    await model.save()
            else:
                logger.info(f"[{provider}] No unassigned models to link")

            migrated.append(provider)

        except Exception as e:
            logger.error(
                f"[{provider}] Migration FAILED: {type(e).__name__}: {e}",
                exc_info=True,
            )
            errors.append(f"{provider}: {e}")

    logger.info(
        f"=== Environment variable migration complete === "
        f"migrated={len(migrated)} skipped={len(skipped)} "
        f"not_configured={len(not_configured)} errors={len(errors)}"
    )
    if migrated:
        logger.info(f"  Migrated: {', '.join(migrated)}")
    if skipped:
        logger.info(f"  Skipped (already in DB): {', '.join(skipped)}")
    if errors:
        logger.error(f"  Errors: {'; '.join(errors)}")

    return {
        "message": f"Migration complete. Migrated {len(migrated)} providers.",
        "migrated": migrated,
        "skipped": skipped,
        "not_configured": not_configured,
        "errors": errors,
    }
