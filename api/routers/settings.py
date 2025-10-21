import os

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import SettingsResponse, SettingsUpdate
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get all application settings."""
    try:
        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]

        settings.apply_provider_credentials()

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            provider_credentials=settings.provider_credentials or {},
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching settings: {str(e)}")


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(settings_update: SettingsUpdate):
    """Update application settings."""
    try:
        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]

        # Update only provided fields
        if settings_update.default_content_processing_engine_doc is not None:
            # Cast to proper literal type
            from typing import Literal, cast
            settings.default_content_processing_engine_doc = cast(
                Literal["auto", "docling", "simple"],
                settings_update.default_content_processing_engine_doc
            )
        if settings_update.default_content_processing_engine_url is not None:
            from typing import Literal, cast
            settings.default_content_processing_engine_url = cast(
                Literal["auto", "firecrawl", "jina", "simple"],
                settings_update.default_content_processing_engine_url
            )
        if settings_update.default_embedding_option is not None:
            from typing import Literal, cast
            settings.default_embedding_option = cast(
                Literal["ask", "always", "never"],
                settings_update.default_embedding_option
            )
        if settings_update.auto_delete_files is not None:
            from typing import Literal, cast
            settings.auto_delete_files = cast(
                Literal["yes", "no"],
                settings_update.auto_delete_files
            )
        if settings_update.youtube_preferred_languages is not None:
            settings.youtube_preferred_languages = settings_update.youtube_preferred_languages

        if settings_update.provider_credentials is not None:
            if settings.provider_credentials is None:
                settings.provider_credentials = {}

            for raw_key, raw_value in settings_update.provider_credentials.items():
                if raw_key is None:
                    continue

                normalized_key = raw_key.strip()
                if not normalized_key:
                    continue

                normalized_key = normalized_key.upper()

                if raw_value is None:
                    settings.provider_credentials.pop(normalized_key, None)
                    os.environ.pop(normalized_key, None)
                    continue

                trimmed_value = raw_value.strip()
                if trimmed_value:
                    settings.provider_credentials[normalized_key] = trimmed_value
                    os.environ[normalized_key] = trimmed_value
                else:
                    settings.provider_credentials.pop(normalized_key, None)
                    os.environ.pop(normalized_key, None)

            settings.provider_credentials = {
                key: value
                for key, value in settings.provider_credentials.items()
                if value
            }

        await settings.update()

        settings.apply_provider_credentials()

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            provider_credentials=settings.provider_credentials or {},
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")