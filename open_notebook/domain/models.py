from typing import ClassVar, Optional

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel, RecordModel


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


# todo: future: colocar um cache aqui
class DefaultModels(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_models"

    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    # default_vision_model: Optional[str] = None
    default_embedding_model: Optional[str] = None
