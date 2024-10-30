from typing import ClassVar, Optional

from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.base import ObjectModel
from open_notebook.repository import (
    repo_query,
    repo_update,
)


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    name: str
    provider: str
    type: str


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
            logger.debug(result)
            return DefaultModels(**result[0])

    @classmethod
    def update(self, data):
        repo_update("open_notebook:default_models", data)
