from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import SettingsResponse, SettingsUpdate
from open_notebook.domain.content_settings import ContentSettings
from open_notebook.exceptions import (
    InvalidInputError,
    OpenNotebookError,
)
from open_notebook.utils.url_validation import validate_url

router = APIRouter()


def _blank_to_none(value: str) -> Optional[str]:
    """Strip a free-text setting; an empty value means "unset"."""
    return value.strip() or None


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
            docling_ocr=settings.docling_ocr,
            docling_formulas=settings.docling_formulas,
            docling_vision=settings.docling_vision,
            docling_vision_url=settings.docling_vision_url,
            docling_vision_model=settings.docling_vision_model,
            docling_vision_prompt=settings.docling_vision_prompt,
            youtube_preferred_languages=settings.youtube_preferred_languages,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching settings")


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(settings_update: SettingsUpdate):
    """Update application settings."""
    try:
        # Validate before touching the settings singleton: a rejected request
        # must not leave other fields of the same PUT applied in memory.
        vision_url: Optional[str] = None
        if settings_update.docling_vision_url is not None:
            vision_url = _blank_to_none(settings_update.docling_vision_url)
            if vision_url:
                # The worker sends document images to this URL, so it gets the
                # same SSRF check as every other user-supplied URL.
                try:
                    await validate_url(vision_url, "docling_vision")
                except ValueError as e:
                    raise InvalidInputError(str(e)) from e

        settings: ContentSettings = await ContentSettings.get_instance()  # type: ignore[assignment]

        # Update only provided fields
        if settings_update.default_content_processing_engine_doc is not None:
            # Cast to proper literal type
            from typing import Literal, cast

            settings.default_content_processing_engine_doc = cast(
                Literal["auto", "docling", "simple"],
                settings_update.default_content_processing_engine_doc,
            )
        if settings_update.default_content_processing_engine_url is not None:
            from typing import Literal, cast

            settings.default_content_processing_engine_url = cast(
                Literal["auto", "firecrawl", "jina", "crawl4ai", "simple"],
                settings_update.default_content_processing_engine_url,
            )
        if settings_update.default_embedding_option is not None:
            from typing import Literal, cast

            settings.default_embedding_option = cast(
                Literal["ask", "always", "never"],
                settings_update.default_embedding_option,
            )
        if settings_update.auto_delete_files is not None:
            from typing import Literal, cast

            settings.auto_delete_files = cast(
                Literal["yes", "no"], settings_update.auto_delete_files
            )
        if settings_update.docling_ocr is not None:
            settings.docling_ocr = settings_update.docling_ocr
        if settings_update.docling_formulas is not None:
            settings.docling_formulas = settings_update.docling_formulas
        if settings_update.docling_vision is not None:
            settings.docling_vision = settings_update.docling_vision
        if settings_update.docling_vision_url is not None:
            settings.docling_vision_url = vision_url
        if settings_update.docling_vision_model is not None:
            settings.docling_vision_model = _blank_to_none(
                settings_update.docling_vision_model
            )
        if settings_update.docling_vision_prompt is not None:
            settings.docling_vision_prompt = _blank_to_none(
                settings_update.docling_vision_prompt
            )
        if settings_update.youtube_preferred_languages is not None:
            settings.youtube_preferred_languages = (
                settings_update.youtube_preferred_languages
            )

        await settings.update()

        return SettingsResponse(
            default_content_processing_engine_doc=settings.default_content_processing_engine_doc,
            default_content_processing_engine_url=settings.default_content_processing_engine_url,
            default_embedding_option=settings.default_embedding_option,
            auto_delete_files=settings.auto_delete_files,
            docling_ocr=settings.docling_ocr,
            docling_formulas=settings.docling_formulas,
            docling_vision=settings.docling_vision,
            docling_vision_url=settings.docling_vision_url,
            docling_vision_model=settings.docling_vision_model,
            docling_vision_prompt=settings.docling_vision_prompt,
            youtube_preferred_languages=settings.youtube_preferred_languages,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating settings")
