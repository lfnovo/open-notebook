from typing import ClassVar, Literal, Optional, Union

from pydantic import field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.base import ObjectModel

WorkspaceType = Literal["personal", "team"]


class Workspace(ObjectModel):
    table_name: ClassVar[str] = "workspace"

    name: str
    type: WorkspaceType
    owner_id: Optional[Union[str, RecordID]] = None
    team_id: Optional[Union[str, RecordID]] = None
    created_by: Optional[Union[str, RecordID]] = None

    @field_validator("owner_id", "team_id", "created_by", mode="before")
    @classmethod
    def parse_record_id(cls, value):
        if isinstance(value, str) and value:
            return ensure_record_id(value)
        return value
