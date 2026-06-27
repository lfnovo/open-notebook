"""
Transformations service layer using API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from api.client import api_client
from open_notebook.domain.transformation import Transformation


class TransformationsService:
    """Service layer for transformations operations using API."""

    def __init__(self):
        logger.info("Using API for transformations operations")

    def _build_transformation(self, trans_data: Dict[str, Any]) -> Transformation:
        transformation = Transformation(
            name=trans_data["name"],
            title=trans_data["title"],
            description=trans_data["description"],
            prompt=trans_data["prompt"],
            apply_default=trans_data["apply_default"],
            model_id=trans_data.get("model_id"),
        )
        transformation.id = trans_data["id"]
        transformation.created = datetime.fromisoformat(
            trans_data["created"].replace("Z", "+00:00")
        )
        transformation.updated = datetime.fromisoformat(
            trans_data["updated"].replace("Z", "+00:00")
        )
        return transformation

    def get_all_transformations(self) -> List[Transformation]:
        """Get all transformations."""
        transformations_data = api_client.get_transformations()
        # Convert API response to Transformation objects
        transformations = []
        for trans_data in transformations_data:
            transformations.append(self._build_transformation(trans_data))
        return transformations

    def get_transformation(self, transformation_id: str) -> Transformation:
        """Get a specific transformation."""
        response = api_client.get_transformation(transformation_id)
        trans_data = response if isinstance(response, dict) else response[0]
        return self._build_transformation(trans_data)

    def create_transformation(
        self,
        name: str,
        title: str,
        description: str,
        prompt: str,
        apply_default: bool = False,
    ) -> Transformation:
        """Create a new transformation."""
        response = api_client.create_transformation(
            name=name,
            title=title,
            description=description,
            prompt=prompt,
            apply_default=apply_default,
        )
        trans_data = response if isinstance(response, dict) else response[0]
        return self._build_transformation(trans_data)

    def update_transformation(self, transformation: Transformation) -> Transformation:
        """Update a transformation."""
        if not transformation.id:
            raise ValueError("Transformation ID is required for update")

        updates = {
            "name": transformation.name,
            "title": transformation.title,
            "description": transformation.description,
            "prompt": transformation.prompt,
            "apply_default": transformation.apply_default,
            "model_id": transformation.model_id,
        }
        response = api_client.update_transformation(transformation.id, **updates)
        trans_data = response if isinstance(response, dict) else response[0]

        # Update the transformation object with the response
        transformation.name = trans_data["name"]
        transformation.title = trans_data["title"]
        transformation.description = trans_data["description"]
        transformation.prompt = trans_data["prompt"]
        transformation.apply_default = trans_data["apply_default"]
        transformation.model_id = trans_data.get("model_id")
        transformation.updated = datetime.fromisoformat(
            trans_data["updated"].replace("Z", "+00:00")
        )

        return transformation

    def delete_transformation(self, transformation_id: str) -> bool:
        """Delete a transformation."""
        api_client.delete_transformation(transformation_id)
        return True

    def execute_transformation(
        self, transformation_id: str, input_text: str, model_id: Optional[str] = None
    ) -> Union[Dict[Any, Any], List[Dict[Any, Any]]]:
        """Execute a transformation on input text."""
        result = api_client.execute_transformation(
            transformation_id=transformation_id,
            input_text=input_text,
            model_id=model_id,
        )
        return result


# Global service instance
transformations_service = TransformationsService()
