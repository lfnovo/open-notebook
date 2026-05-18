from typing import Any, ClassVar, Dict, Optional

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError


class SourceAnalysis(ObjectModel):
    table_name: ClassVar[str] = "source_analysis"
    nullable_fields: ClassVar[set[str]] = {
        "raw_output",
        "normalized_output",
        "rendered_markdown",
    }

    source: str
    capability: str
    provider: str
    model: str
    status: str
    raw_output: Optional[Dict[str, Any]] = None
    normalized_output: Optional[Dict[str, Any]] = None
    rendered_markdown: Optional[str] = None

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        data["source"] = ensure_record_id(self.source)
        return data

    async def get_source(self):
        try:
            from open_notebook.domain.notebook import Source

            source = await repo_query("SELECT * FROM $id", {"id": ensure_record_id(self.source)})
            return Source(**source[0]) if source else None
        except Exception as e:
            raise DatabaseOperationError(e)
