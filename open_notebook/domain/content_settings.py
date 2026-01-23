from typing import ClassVar, List, Literal, Optional

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
    youtube_preferred_languages: Optional[List[str]] = Field(
        ["en", "pt", "es", "de", "nl", "en-GB", "fr", "de", "hi", "ja"],
        description="Preferred languages for YouTube transcripts",
    )
    smol_docling_enabled: bool = Field(
        False, description="Enable Smol Docling Integration (Preview)"
    )
    document_parser: Optional[Literal["content_core", "smol_docling"]] = Field(
        "content_core",
        description="Document parser to use: content_core (default) or smol_docling (VLM-based)"
    )
    smol_docling_use_gpu: bool = Field(
        True, description="Use GPU acceleration for SmolDocling (if available)"
    )
