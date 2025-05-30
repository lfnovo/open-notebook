from typing import ClassVar, Literal, Optional

from pydantic import Field

from open_notebook.domain.base import RecordModel


class ContentSettings(RecordModel):
    record_id: ClassVar[str] = "open_notebook:content_settings"
    default_content_processing_engine_doc: Optional[
        Literal["auto", "docling", "simple"]
    ] = Field("auto", description="Default Content Processing Engine for Documents")
    default_content_processing_engine_url: Optional[
        Literal["auto", "firecrawl", "jina", "simple"]
    ] = Field("auto", description="Default Content Processing Engine for URLs")
    default_embedding_option: Optional[Literal["ask", "always", "never"]] = Field(
        "ask", description="Default Embedding Option for Vector Search"
    )
    auto_delete_files: Optional[Literal["yes", "no"]] = Field(
        "yes", description="Auto Delete Uploaded Files"
    )
