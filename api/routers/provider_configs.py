"""
Provider Configurations Router

Provides endpoints for managing multiple API key configurations per provider.
Each provider can have multiple configurations with different credentials.

Endpoints:
- GET /api-keys/configs - List all provider configurations
- GET /api-keys/configs/{provider} - List configurations for a provider
- POST /api-keys/configs/{provider} - Create a new configuration
- GET /api-keys/configs/{provider}/{config_id} - Get a specific configuration
- PUT /api-keys/configs/{provider}/{config_id} - Update a configuration
- DELETE /api-keys/configs/{provider}/{config_id} - Delete a configuration
- PUT /api-keys/configs/{provider}/{config_id}/default - Set as default

NEVER returns actual API key values - only configuration metadata.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from pydantic import SecretStr as PydanticSecretStr

from open_notebook.domain.provider_config import ProviderConfig, ProviderCredential

router = APIRouter(prefix="/api-keys/configs", tags=["provider-configs"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateProviderConfigRequest(BaseModel):
    """Request to create a new provider configuration."""

    name: str = Field(default="Default", description="Configuration name")
    api_key: Optional[str] = Field(None, description="API key (will be stored encrypted)")
    base_url: Optional[str] = Field(None, description="Base URL for the provider")
    model: Optional[str] = Field(None, description="Default model to use")
    api_version: Optional[str] = Field(None, description="API version")
    endpoint: Optional[str] = Field(None, description="Generic endpoint URL")
    endpoint_llm: Optional[str] = Field(None, description="LLM endpoint URL")
    endpoint_embedding: Optional[str] = Field(None, description="Embedding endpoint URL")
    endpoint_stt: Optional[str] = Field(None, description="Speech-to-text endpoint URL")
    endpoint_tts: Optional[str] = Field(None, description="Text-to-speech endpoint URL")
    project: Optional[str] = Field(None, description="Project ID (for Vertex AI)")
    location: Optional[str] = Field(None, description="Location/region (for Vertex AI)")
    credentials_path: Optional[str] = Field(
        None, description="Path to credentials file (for Vertex AI)"
    )
    is_default: Optional[bool] = Field(
        default=None, description="Set as default configuration"
    )

    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Reject empty strings - convert to None."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class UpdateProviderConfigRequest(BaseModel):
    """Request to update an existing provider configuration."""

    name: Optional[str] = Field(None, description="Configuration name")
    api_key: Optional[str] = Field(None, description="API key (will be stored encrypted)")
    base_url: Optional[str] = Field(None, description="Base URL for the provider")
    model: Optional[str] = Field(None, description="Default model to use")
    api_version: Optional[str] = Field(None, description="API version")
    endpoint: Optional[str] = Field(None, description="Generic endpoint URL")
    endpoint_llm: Optional[str] = Field(None, description="LLM endpoint URL")
    endpoint_embedding: Optional[str] = Field(None, description="Embedding endpoint URL")
    endpoint_stt: Optional[str] = Field(None, description="Speech-to-text endpoint URL")
    endpoint_tts: Optional[str] = Field(None, description="Text-to-speech endpoint URL")
    project: Optional[str] = Field(None, description="Project ID (for Vertex AI)")
    location: Optional[str] = Field(None, description="Location/region (for Vertex AI)")
    credentials_path: Optional[str] = Field(
        None, description="Path to credentials file (for Vertex AI)"
    )
    is_default: Optional[bool] = Field(
        default=None, description="Set as default configuration"
    )

    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Reject empty strings - convert to None."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class ProviderConfigResponse(BaseModel):
    """Response for a provider configuration."""

    id: str = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    provider: str = Field(..., description="Provider name")
    is_default: bool = Field(..., description="Whether this is the default configuration")
    base_url: Optional[str] = Field(None, description="Base URL")
    model: Optional[str] = Field(None, description="Default model")
    api_version: Optional[str] = Field(None, description="API version")
    endpoint: Optional[str] = Field(None, description="Generic endpoint")
    endpoint_llm: Optional[str] = Field(None, description="LLM endpoint")
    endpoint_embedding: Optional[str] = Field(None, description="Embedding endpoint")
    endpoint_stt: Optional[str] = Field(None, description="STT endpoint")
    endpoint_tts: Optional[str] = Field(None, description="TTS endpoint")
    project: Optional[str] = Field(None, description="Project ID")
    location: Optional[str] = Field(None, description="Location/region")
    credentials_path: Optional[str] = Field(None, description="Credentials path")
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")

    class Config:
        # api_key is NEVER included in responses for security
        populate_by_name = True


class ProviderConfigsListResponse(BaseModel):
    """Response listing all configurations for a provider."""

    provider: str = Field(..., description="Provider name")
    configs: List[ProviderConfigResponse] = Field(..., description="List of configurations")
    default_config_id: Optional[str] = Field(
        None, description="ID of the default configuration"
    )


class AllProviderConfigsResponse(BaseModel):
    """Response listing all configurations for all providers."""

    providers: dict[str, ProviderConfigsListResponse] = Field(
        ..., description="Configurations organized by provider"
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("", response_model=AllProviderConfigsResponse)
async def list_all_configs():
    """
    Get all provider configurations.

    Returns all configurations for all providers, organized by provider.
    NEVER returns API key values.
    """
    try:
        config = await ProviderConfig.get_instance()

        result = {}
        for provider, credentials in config.credentials.items():
            default_id = None
            configs = []

            for cred in credentials:
                resp = ProviderConfigResponse(
                    id=cred.id,
                    name=cred.name,
                    provider=cred.provider,
                    is_default=cred.is_default,
                    base_url=cred.base_url,
                    model=cred.model,
                    api_version=cred.api_version,
                    endpoint=cred.endpoint,
                    endpoint_llm=cred.endpoint_llm,
                    endpoint_embedding=cred.endpoint_embedding,
                    endpoint_stt=cred.endpoint_stt,
                    endpoint_tts=cred.endpoint_tts,
                    project=cred.project,
                    location=cred.location,
                    credentials_path=cred.credentials_path,
                    created=cred.created,
                    updated=cred.updated,
                )
                configs.append(resp)

                if cred.is_default:
                    default_id = cred.id

            result[provider] = ProviderConfigsListResponse(
                provider=provider,
                configs=configs,
                default_config_id=default_id,
            )

        return AllProviderConfigsResponse(providers=result)

    except Exception as e:
        logger.error(f"Error fetching all configurations: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching configurations: {str(e)}"
        )


@router.get("/{provider}", response_model=ProviderConfigsListResponse)
async def list_provider_configs(provider: str):
    """
    Get all configurations for a specific provider.

    Returns all configurations for the specified provider.
    NEVER returns API key values.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()
        credentials = config.credentials.get(provider_lower, [])

        default_id = None
        configs = []

        for cred in credentials:
            resp = ProviderConfigResponse(
                id=cred.id,
                name=cred.name,
                provider=cred.provider,
                is_default=cred.is_default,
                base_url=cred.base_url,
                model=cred.model,
                api_version=cred.api_version,
                endpoint=cred.endpoint,
                endpoint_llm=cred.endpoint_llm,
                endpoint_embedding=cred.endpoint_embedding,
                endpoint_stt=cred.endpoint_stt,
                endpoint_tts=cred.endpoint_tts,
                project=cred.project,
                location=cred.location,
                credentials_path=cred.credentials_path,
                created=cred.created,
                updated=cred.updated,
            )
            configs.append(resp)

            if cred.is_default:
                default_id = cred.id

        return ProviderConfigsListResponse(
            provider=provider_lower,
            configs=configs,
            default_config_id=default_id,
        )

    except Exception as e:
        logger.error(f"Error fetching configurations for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching configurations: {str(e)}",
        )


@router.post("/{provider}", response_model=ProviderConfigResponse, status_code=201)
async def create_provider_config(
    provider: str, request: CreateProviderConfigRequest
):
    """
    Create a new configuration for a provider.

    The first configuration for a provider is automatically set as the default.
    Subsequent configurations can be set as default by setting is_default=True.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()

        # Generate unique config ID
        config_id = f"{provider_lower}:{uuid.uuid4().hex[:8]}"

        # Check existing configs for this provider
        existing = config.credentials.get(provider_lower, [])

        # Determine if this should be the default
        is_default = len(existing) == 0
        if request.is_default is True:
            is_default = True

        # Create SecretStr for API key if provided
        api_key_str = request.api_key
        api_key = PydanticSecretStr(api_key_str) if api_key_str else None

        # Create the credential
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cred = ProviderCredential(
            id=config_id,
            name=request.name or "Default",
            provider=provider_lower,
            is_default=is_default,
            api_key=api_key,
            base_url=request.base_url,
            model=request.model,
            api_version=request.api_version,
            endpoint=request.endpoint,
            endpoint_llm=request.endpoint_llm,
            endpoint_embedding=request.endpoint_embedding,
            endpoint_stt=request.endpoint_stt,
            endpoint_tts=request.endpoint_tts,
            project=request.project,
            location=request.location,
            credentials_path=request.credentials_path,
            created=now,
            updated=now,
        )

        # If this is the default, unset other defaults
        if is_default and existing:
            for existing_cred in existing:
                existing_cred.is_default = False

        # Add to the provider's configs
        if provider_lower not in config.credentials:
            config.credentials[provider_lower] = []
        config.credentials[provider_lower].append(cred)

        # Save to database
        await config.save()

        return ProviderConfigResponse(
            id=cred.id,
            name=cred.name,
            provider=cred.provider,
            is_default=cred.is_default,
            base_url=cred.base_url,
            model=cred.model,
            api_version=cred.api_version,
            endpoint=cred.endpoint,
            endpoint_llm=cred.endpoint_llm,
            endpoint_embedding=cred.endpoint_embedding,
            endpoint_stt=cred.endpoint_stt,
            endpoint_tts=cred.endpoint_tts,
            project=cred.project,
            location=cred.location,
            credentials_path=cred.credentials_path,
            created=cred.created,
            updated=cred.updated,
        )

    except Exception as e:
        logger.error(f"Error creating configuration for {provider}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating configuration: {str(e)}"
        )


@router.get("/{provider}/{config_id}", response_model=ProviderConfigResponse)
async def get_provider_config(provider: str, config_id: str):
    """
    Get a specific configuration by ID.

    NEVER returns the API key value for security.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()
        credentials = config.credentials.get(provider_lower, [])

        for cred in credentials:
            if cred.id == config_id:
                return ProviderConfigResponse(
                    id=cred.id,
                    name=cred.name,
                    provider=cred.provider,
                    is_default=cred.is_default,
                    base_url=cred.base_url,
                    model=cred.model,
                    api_version=cred.api_version,
                    endpoint=cred.endpoint,
                    endpoint_llm=cred.endpoint_llm,
                    endpoint_embedding=cred.endpoint_embedding,
                    endpoint_stt=cred.endpoint_stt,
                    endpoint_tts=cred.endpoint_tts,
                    project=cred.project,
                    location=cred.location,
                    credentials_path=cred.credentials_path,
                    created=cred.created,
                    updated=cred.updated,
                )

        raise HTTPException(status_code=404, detail="Configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching configuration {config_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching configuration: {str(e)}"
        )


@router.put("/{provider}/{config_id}", response_model=ProviderConfigResponse)
async def update_provider_config(
    provider: str, config_id: str, request: UpdateProviderConfigRequest
):
    """
    Update a specific configuration.

    If is_default=True is set, this configuration will become the default
    and all other configurations for this provider will have is_default=False.
    NEVER returns the API key value for security.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()
        credentials = config.credentials.get(provider_lower, [])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for cred in credentials:
            if cred.id == config_id:
                # Update fields if provided
                if request.name is not None:
                    cred.name = request.name
                if request.api_key is not None:
                    cred.api_key = PydanticSecretStr(request.api_key)
                if request.base_url is not None:
                    cred.base_url = request.base_url
                if request.model is not None:
                    cred.model = request.model
                if request.api_version is not None:
                    cred.api_version = request.api_version
                if request.endpoint is not None:
                    cred.endpoint = request.endpoint
                if request.endpoint_llm is not None:
                    cred.endpoint_llm = request.endpoint_llm
                if request.endpoint_embedding is not None:
                    cred.endpoint_embedding = request.endpoint_embedding
                if request.endpoint_stt is not None:
                    cred.endpoint_stt = request.endpoint_stt
                if request.endpoint_tts is not None:
                    cred.endpoint_tts = request.endpoint_tts
                if request.project is not None:
                    cred.project = request.project
                if request.location is not None:
                    cred.location = request.location
                if request.credentials_path is not None:
                    cred.credentials_path = request.credentials_path

                # Handle default setting
                if request.is_default is True:
                    # Unset other defaults
                    for other in credentials:
                        other.is_default = False
                    cred.is_default = True

                cred.updated = now

                # Save to database
                await config.save()

                return ProviderConfigResponse(
                    id=cred.id,
                    name=cred.name,
                    provider=cred.provider,
                    is_default=cred.is_default,
                    base_url=cred.base_url,
                    model=cred.model,
                    api_version=cred.api_version,
                    endpoint=cred.endpoint,
                    endpoint_llm=cred.endpoint_llm,
                    endpoint_embedding=cred.endpoint_embedding,
                    endpoint_stt=cred.endpoint_stt,
                    endpoint_tts=cred.endpoint_tts,
                    project=cred.project,
                    location=cred.location,
                    credentials_path=cred.credentials_path,
                    created=cred.created,
                    updated=cred.updated,
                )

        raise HTTPException(status_code=404, detail="Configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating configuration {config_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating configuration: {str(e)}"
        )


@router.delete("/{provider}/{config_id}", status_code=204)
async def delete_provider_config(provider: str, config_id: str):
    """
    Delete a specific configuration.

    Cannot delete the default configuration if there are other configurations.
    Set another config as default first, then delete.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()
        credentials = config.credentials.get(provider_lower, [])

        for i, cred in enumerate(credentials):
            if cred.id == config_id:
                # Check if trying to delete default with other configs present
                if cred.is_default and len(credentials) > 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot delete default configuration. Set another config as default first.",
                    )

                del credentials[i]
                await config.save()
                return

        raise HTTPException(status_code=404, detail="Configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting configuration {config_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting configuration: {str(e)}"
        )


@router.put("/{provider}/{config_id}/default", response_model=ProviderConfigResponse)
async def set_default_config(provider: str, config_id: str):
    """
    Set a configuration as the default for its provider.

    The previous default configuration will have is_default set to False.
    """
    try:
        config = await ProviderConfig.get_instance()
        provider_lower = provider.lower()
        credentials = config.credentials.get(provider_lower, [])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for cred in credentials:
            if cred.id == config_id:
                # Set this as default, unset others
                cred.is_default = True
                cred.updated = now

                for other in credentials:
                    if other.id != config_id:
                        other.is_default = False

                await config.save()

                return ProviderConfigResponse(
                    id=cred.id,
                    name=cred.name,
                    provider=cred.provider,
                    is_default=cred.is_default,
                    base_url=cred.base_url,
                    model=cred.model,
                    api_version=cred.api_version,
                    endpoint=cred.endpoint,
                    endpoint_llm=cred.endpoint_llm,
                    endpoint_embedding=cred.endpoint_embedding,
                    endpoint_stt=cred.endpoint_stt,
                    endpoint_tts=cred.endpoint_tts,
                    project=cred.project,
                    location=cred.location,
                    credentials_path=cred.credentials_path,
                    created=cred.created,
                    updated=cred.updated,
                )

        raise HTTPException(status_code=404, detail="Configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default configuration: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error setting default: {str(e)}"
        )
