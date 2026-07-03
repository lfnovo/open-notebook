from typing import Any, ClassVar, Dict, Optional

from pydantic import Field

from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.base import ObjectModel, RecordModel


class Transformation(ObjectModel):
    table_name: ClassVar[str] = "transformation"
    nullable_fields: ClassVar[set[str]] = {"model_id"}
    name: str
    title: str
    description: str
    prompt: str
    apply_default: bool
    model_id: Optional[str] = None

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        if data.get("model_id"):
            data["model_id"] = ensure_record_id(data["model_id"])
        return data


class DefaultPrompts(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_prompts"
    transformation_instructions: Optional[str] = Field(
        None, description="Instructions for executing a transformation"
    )
