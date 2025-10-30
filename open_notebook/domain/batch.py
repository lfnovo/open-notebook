from __future__ import annotations

from typing import ClassVar, Optional

from open_notebook.domain.base import ObjectModel


class BatchUpload(ObjectModel):
    table_name: ClassVar[str] = "batch_upload"
    name: Optional[str] = None
    status: str = "processing"
    total_files: int
    processed_files: int = 0
    failed_files: int = 0

class BatchSourceRelationship(ObjectModel):
    table_name: ClassVar[str] = "batch_source_relationship"
    batch_id: str
    source_id: str
    file_name: str
    status: str = "pending"
    error_message: Optional[str] = None