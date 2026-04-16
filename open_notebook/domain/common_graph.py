from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import InvalidInputError


class CommonGraph(ObjectModel):
    table_name: ClassVar[str] = "common_graph"

    title: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    status: str = "started"
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("source_ids", mode="before")
    @classmethod
    def validate_source_ids(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise InvalidInputError("source_ids must be a list")
        if len(value) < 2:
            raise InvalidInputError("Common graph requires at least two source IDs")
        return [str(source_id) for source_id in value]

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        data["source_ids"] = [str(source_id) for source_id in self.source_ids]
        print(f"Prepared data for saving CommonGraph: {data}")
        return data
