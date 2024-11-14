from typing import ClassVar, List, Optional

import yaml
from pydantic import Field

from open_notebook.domain.base import RecordModel


class Transformation:
    @classmethod
    def get_all(cls):
        with open("transformations.yaml", "r") as file:
            transformations = yaml.safe_load(file)
        return transformations


class DefaultTransformations(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_transformations"
    source_insights: Optional[List[str]] = Field(default_factory=list)
