"""
Settings service layer using API.
"""


from loguru import logger

from api.client import api_client
from open_notebook.domain.content_settings import ContentSettings


class SettingsService:
    """Service layer for settings operations using API."""
    
    def __init__(self):
        logger.info("Using API for settings operations")
    
    def get_settings(self) -> ContentSettings:
        """Get application settings."""
        settings_response = api_client.get_settings()
        settings_data = settings_response if isinstance(settings_response, dict) else settings_response[0]

        # Create ContentSettings object from API response
        settings = ContentSettings(
            default_content_processing_engine_doc=settings_data.get("default_content_processing_engine_doc"),
            default_content_processing_engine_url=settings_data.get("default_content_processing_engine_url"),
            default_embedding_option=settings_data.get("default_embedding_option"),
            auto_delete_files=settings_data.get("auto_delete_files"),
            youtube_preferred_languages=settings_data.get("youtube_preferred_languages"),
        )

        return settings
    
    def update_settings(self, settings: ContentSettings) -> ContentSettings:
        """Update application settings."""
        updates = {
            "default_content_processing_engine_doc": settings.default_content_processing_engine_doc,
            "default_content_processing_engine_url": settings.default_content_processing_engine_url,
            "default_embedding_option": settings.default_embedding_option,
            "auto_delete_files": settings.auto_delete_files,
            "youtube_preferred_languages": settings.youtube_preferred_languages,
        }

        settings_response = api_client.update_settings(**updates)
        settings_data = settings_response if isinstance(settings_response, dict) else settings_response[0]

        # Update the settings object with the response
        settings.default_content_processing_engine_doc = settings_data.get("default_content_processing_engine_doc")
        settings.default_content_processing_engine_url = settings_data.get("default_content_processing_engine_url")
        settings.default_embedding_option = settings_data.get("default_embedding_option")
        settings.auto_delete_files = settings_data.get("auto_delete_files")
        settings.youtube_preferred_languages = settings_data.get("youtube_preferred_languages")

        return settings


# Global service instance
settings_service = SettingsService()