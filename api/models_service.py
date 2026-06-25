"""
Models service layer using API.
"""

from typing import List, Optional

from loguru import logger

from api.client import api_client
from open_notebook.ai.models import DefaultModels, Model


class ModelsService:
    """Service layer for models operations using API."""

    def __init__(self):
        logger.info("Using API for models operations")

    def get_all_models(self, model_type: Optional[str] = None) -> List[Model]:
        """Get all models with optional type filtering."""
        models_data = api_client.get_models(model_type=model_type)
        # Convert API response to Model objects
        models = []
        for model_data in models_data:
            model = Model(
                name=model_data["name"],
                provider=model_data["provider"],
                type=model_data["type"],
            )
            model.id = model_data["id"]
            model.created = model_data["created"]
            model.updated = model_data["updated"]
            models.append(model)
        return models

    def create_model(self, name: str, provider: str, model_type: str) -> Model:
        """Create a new model."""
        response = api_client.create_model(name, provider, model_type)
        model_data = response if isinstance(response, dict) else response[0]
        model = Model(
            name=model_data["name"],
            provider=model_data["provider"],
            type=model_data["type"],
        )
        model.id = model_data["id"]
        model.created = model_data["created"]
        model.updated = model_data["updated"]
        return model

    def delete_model(self, model_id: str) -> bool:
        """Delete a model."""
        api_client.delete_model(model_id)
        return True

    def get_default_models(self) -> DefaultModels:
        """Get default model assignments."""
        response = api_client.get_default_models()
        defaults_data = response if isinstance(response, dict) else response[0]
        defaults = DefaultModels()

        # Set the values from API response
        defaults.default_chat_model = defaults_data.get("default_chat_model")
        defaults.default_transformation_model = defaults_data.get(
            "default_transformation_model"
        )
        defaults.large_context_model = defaults_data.get("large_context_model")
        defaults.default_text_to_speech_model = defaults_data.get(
            "default_text_to_speech_model"
        )
        defaults.default_speech_to_text_model = defaults_data.get(
            "default_speech_to_text_model"
        )
        defaults.default_vision_model = defaults_data.get("default_vision_model")
        defaults.default_embedding_model = defaults_data.get("default_embedding_model")
        defaults.default_tools_model = defaults_data.get("default_tools_model")

        return defaults

    def update_default_models(self, defaults: DefaultModels) -> DefaultModels:
        """Update default model assignments."""
        updates = {
            "default_chat_model": defaults.default_chat_model,
            "default_transformation_model": defaults.default_transformation_model,
            "large_context_model": defaults.large_context_model,
            "default_text_to_speech_model": defaults.default_text_to_speech_model,
            "default_speech_to_text_model": defaults.default_speech_to_text_model,
            "default_vision_model": defaults.default_vision_model,
            "default_embedding_model": defaults.default_embedding_model,
            "default_tools_model": defaults.default_tools_model,
        }

        response = api_client.update_default_models(**updates)
        defaults_data = response if isinstance(response, dict) else response[0]

        # Update the defaults object with the response
        defaults.default_chat_model = defaults_data.get("default_chat_model")
        defaults.default_transformation_model = defaults_data.get(
            "default_transformation_model"
        )
        defaults.large_context_model = defaults_data.get("large_context_model")
        defaults.default_text_to_speech_model = defaults_data.get(
            "default_text_to_speech_model"
        )
        defaults.default_speech_to_text_model = defaults_data.get(
            "default_speech_to_text_model"
        )
        defaults.default_vision_model = defaults_data.get("default_vision_model")
        defaults.default_embedding_model = defaults_data.get("default_embedding_model")
        defaults.default_tools_model = defaults_data.get("default_tools_model")

        return defaults


# Global service instance
models_service = ModelsService()
