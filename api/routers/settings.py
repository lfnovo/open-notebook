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

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            smol_docling_enabled=settings.smol_docling_enabled,
            document_parser=settings.document_parser,
            smol_docling_use_gpu=settings.smol_docling_use_gpu,
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
        if settings_update.smol_docling_enabled is not None:
            settings.smol_docling_enabled = settings_update.smol_docling_enabled
        if settings_update.document_parser is not None:
            from typing import Literal, cast
            settings.document_parser = cast(
                Literal["content_core", "smol_docling"],
                settings_update.document_parser
            )
        if settings_update.smol_docling_use_gpu is not None:
            settings.smol_docling_use_gpu = settings_update.smol_docling_use_gpu

        await settings.update()

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            auto_delete_files=settings.auto_delete_files,
            youtube_preferred_languages=settings.youtube_preferred_languages,
            smol_docling_enabled=settings.smol_docling_enabled,
            document_parser=settings.document_parser,
            smol_docling_use_gpu=settings.smol_docling_use_gpu,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")