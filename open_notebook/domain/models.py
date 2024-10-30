from typing import ClassVar, Optional

from pydantic import BaseModel

from open_notebook.database.repository import (
    repo_query,
    repo_update,
)
from open_notebook.domain.base import ObjectModel


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    name: str
    provider: str
    type: str

    @classmethod
    def get_models_by_type(cls, model_type):
        models = repo_query(
            "SELECT * FROM model WHERE type=$model_type;", {"model_type": model_type}
        )
        return [Model(**model) for model in models]


class DefaultModels(BaseModel):
    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    # default_vision_model: Optional[str] = None
    default_embedding_model: Optional[str] = None

    @classmethod
    def load(self):
        result = repo_query("SELECT * FROM open_notebook:default_models;")
        if result:
            result = result[0]
            dm = DefaultModels(**result)
            return dm
        return DefaultModels()

    @classmethod
    def update(self, data):
        repo_update("open_notebook:default_models", data)
