"""
Credentials Router

Thin HTTP layer for managing individual AI provider credentials.
Business logic lives in api.credentials_service.

Endpoints:
- GET /credentials - List all credentials
- GET /credentials/by-provider/{provider} - List credentials for a provider
- POST /credentials - Create a new credential
- GET /credentials/{credential_id} - Get a specific credential
- PUT /credentials/{credential_id} - Update a credential
- DELETE /credentials/{credential_id} - Delete a credential
- POST /credentials/{credential_id}/test - Test connection
- POST /credentials/{credential_id}/discover - Discover models
- POST /credentials/{credential_id}/register-models - Register models

NEVER returns actual API key values - only metadata.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import SecretStr

from api.credentials_service import (
    credential_to_response,
    discover_with_config,
    migrate_from_env as svc_migrate_from_env,
    migrate_from_provider_config as svc_migrate_from_provider_config,
    register_models,
    require_encryption_key,
    test_credential as svc_test_credential,
    validate_url,
)
from api.credentials_service import (
    get_env_status as svc_get_env_status,
    get_provider_status,
)
from api.models import (
    CreateCredentialRequest,
    CredentialDeleteResponse,
    CredentialResponse,
    DiscoveredModelResponse,
    DiscoverModelsResponse,
    RegisterModelsRequest,
    RegisterModelsResponse,
    UpdateCredentialRequest,
)
from open_notebook.domain.credential import Credential

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _handle_value_error(e: ValueError, status_code: int = 400) -> HTTPException:
    """Convert a ValueError from the service layer to an HTTPException."""
    return HTTPException(status_code=status_code, detail=str(e))


# =============================================================================
# Status endpoints
# =============================================================================


@router.get("/status")
async def get_status():
    """
    Get configuration status: encryption key status, and per-provider
    configured/source information.
    """
    try:
        return await get_provider_status()
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credential status")


@router.get("/env-status")
async def get_env_status():
    """Check what's configured via environment variables."""
    try:
        return await svc_get_env_status()
    except Exception as e:
        logger.error(f"Error checking env status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check environment status")


# =============================================================================
# CRUD endpoints
# =============================================================================


@router.get("", response_model=List[CredentialResponse])
async def list_credentials(
    provider: Optional[str] = Query(None, description="Filter by provider"),
):
    """List all credentials, optionally filtered by provider."""
    try:
        if provider:
            credentials = await Credential.get_by_provider(provider)
        else:
            credentials = await Credential.get_all(order_by="provider, created")

        result = []
        for cred in credentials:
            models = await cred.get_linked_models()
            result.append(credential_to_response(cred, len(models)))

        return result

    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to list credentials")


@router.get("/by-provider/{provider}", response_model=List[CredentialResponse])
async def list_credentials_by_provider(provider: str):
    """List all credentials for a specific provider."""
    try:
        credentials = await Credential.get_by_provider(provider.lower())
        result = []
        for cred in credentials:
            models = await cred.get_linked_models()
            result.append(credential_to_response(cred, len(models)))
        return result
    except Exception as e:
        logger.error(f"Error listing credentials for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list credentials for provider")


@router.post("", response_model=CredentialResponse, status_code=201)
async def create_credential(request: CreateCredentialRequest):
    """Create a new credential."""
    try:
        require_encryption_key()
    except ValueError as e:
        raise _handle_value_error(e)

    # Validate all URL fields
    for url_field in [
        request.base_url, request.endpoint, request.endpoint_llm,
        request.endpoint_embedding, request.endpoint_stt, request.endpoint_tts,
    ]:
        if url_field:
            try:
                validate_url(url_field, request.provider)
            except ValueError as e:
                raise _handle_value_error(e)

    try:
        cred = Credential(
            name=request.name,
            provider=request.provider.lower(),
            modalities=request.modalities,
            api_key=SecretStr(request.api_key) if request.api_key else None,
            base_url=request.base_url,
            endpoint=request.endpoint,
            api_version=request.api_version,
            endpoint_llm=request.endpoint_llm,
            endpoint_embedding=request.endpoint_embedding,
            endpoint_stt=request.endpoint_stt,
            endpoint_tts=request.endpoint_tts,
            project=request.project,
            location=request.location,
            credentials_path=request.credentials_path,
        )
        await cred.save()
        return credential_to_response(cred, 0)

    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to create credential")


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(credential_id: str):
    """Get a specific credential by ID. Never returns api_key."""
    try:
        cred = await Credential.get(credential_id)
        models = await cred.get_linked_models()
        return credential_to_response(cred, len(models))
    except Exception as e:
        logger.error(f"Error fetching credential {credential_id}: {e}")
        raise HTTPException(status_code=404, detail="Credential not found")


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(credential_id: str, request: UpdateCredentialRequest):
    """Update an existing credential."""
    try:
        require_encryption_key()
    except ValueError as e:
        raise _handle_value_error(e)

    # Validate all URL fields being updated
    for url_field in [
        request.base_url, request.endpoint, request.endpoint_llm,
        request.endpoint_embedding, request.endpoint_stt, request.endpoint_tts,
    ]:
        if url_field:
            try:
                validate_url(url_field, "update")
            except ValueError as e:
                raise _handle_value_error(e)

    try:
        cred = await Credential.get(credential_id)

        if request.name is not None:
            cred.name = request.name
        if request.modalities is not None:
            cred.modalities = request.modalities
        if request.api_key is not None:
            cred.api_key = SecretStr(request.api_key)
        if request.base_url is not None:
            cred.base_url = request.base_url or None
        if request.endpoint is not None:
            cred.endpoint = request.endpoint or None
        if request.api_version is not None:
            cred.api_version = request.api_version or None
        if request.endpoint_llm is not None:
            cred.endpoint_llm = request.endpoint_llm or None
        if request.endpoint_embedding is not None:
            cred.endpoint_embedding = request.endpoint_embedding or None
        if request.endpoint_stt is not None:
            cred.endpoint_stt = request.endpoint_stt or None
        if request.endpoint_tts is not None:
            cred.endpoint_tts = request.endpoint_tts or None
        if request.project is not None:
            cred.project = request.project or None
        if request.location is not None:
            cred.location = request.location or None
        if request.credentials_path is not None:
            cred.credentials_path = request.credentials_path or None

        await cred.save()
        models = await cred.get_linked_models()
        return credential_to_response(cred, len(models))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update credential")


@router.delete("/{credential_id}", response_model=CredentialDeleteResponse)
async def delete_credential(
    credential_id: str,
    delete_models: bool = Query(False, description="Also delete linked models"),
    migrate_to: Optional[str] = Query(
        None, description="Migrate linked models to this credential ID"
    ),
):
    """
    Delete a credential.

    If the credential has linked models:
    - Pass delete_models=true to delete them
    - Pass migrate_to=<credential_id> to reassign them
    - Without either, returns 409 with linked model info
    """
    try:
        cred = await Credential.get(credential_id)
        linked_models = await cred.get_linked_models()

        if linked_models and not delete_models and not migrate_to:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"Credential has {len(linked_models)} linked model(s)",
                    "model_ids": [m.id for m in linked_models],
                    "model_names": [f"{m.provider}/{m.name}" for m in linked_models],
                },
            )

        deleted_models = 0

        if linked_models and migrate_to:
            # Migrate models to another credential
            target_cred = await Credential.get(migrate_to)
            for model in linked_models:
                model.credential = target_cred.id
                await model.save()

        elif linked_models and delete_models:
            # Delete linked models
            for model in linked_models:
                await model.delete()
                deleted_models += 1

        # Delete the credential
        await cred.delete()

        return CredentialDeleteResponse(
            message="Credential deleted successfully",
            deleted_models=deleted_models,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")


# =============================================================================
# Test / Discover / Register endpoints
# =============================================================================


@router.post("/{credential_id}/test")
async def test_credential(credential_id: str):
    """Test connection using this credential's configuration."""
    return await svc_test_credential(credential_id)


@router.post("/{credential_id}/discover", response_model=DiscoverModelsResponse)
async def discover_models_for_credential(credential_id: str):
    """Discover available models using this credential's API key."""
    try:
        cred = await Credential.get(credential_id)
        config = cred.to_esperanto_config()
        provider = cred.provider.lower()

        discovered = await discover_with_config(provider, config)

        return DiscoverModelsResponse(
            credential_id=cred.id or "",
            provider=provider,
            discovered=[
                DiscoveredModelResponse(
                    name=d["name"],
                    provider=d["provider"],
                    description=d.get("description"),
                )
                for d in discovered
            ],
        )

    except Exception as e:
        logger.error(f"Error discovering models for credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to discover models")


@router.post("/{credential_id}/register-models", response_model=RegisterModelsResponse)
async def register_models_for_credential(
    credential_id: str, request: RegisterModelsRequest
):
    """Register discovered models and link them to this credential."""
    try:
        result = await register_models(credential_id, request.models)
        return RegisterModelsResponse(**result)
    except Exception as e:
        logger.error(f"Error registering models for credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to register models")


# =============================================================================
# Migration endpoints
# =============================================================================


@router.post("/migrate-from-provider-config")
async def migrate_from_provider_config():
    """Migrate existing ProviderConfig data to individual credential records."""
    try:
        return await svc_migrate_from_provider_config()
    except ValueError as e:
        raise _handle_value_error(e)
    except Exception as e:
        logger.error(f"ProviderConfig migration FAILED: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Migration from provider config failed")


@router.post("/migrate-from-env")
async def migrate_from_env():
    """Migrate API keys from environment variables to credential records."""
    try:
        return await svc_migrate_from_env()
    except ValueError as e:
        raise _handle_value_error(e)
    except Exception as e:
        logger.error(f"Env migration FAILED: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Migration from environment variables failed")
