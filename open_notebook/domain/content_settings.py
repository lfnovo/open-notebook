from typing import ClassVar, List, Literal, Optional

from pydantic import Field

from open_notebook.domain.base import RecordModel


class ContentSettings(RecordModel):
    record_id: ClassVar[str] = "open_notebook:content_settings"
    default_content_processing_engine_doc: Optional[
        Literal["auto", "docling", "simple"]
    ] = Field("auto", description="Default Content Processing Engine for Documents")
    default_content_processing_engine_url: Optional[
        Literal["auto", "firecrawl", "jina", "crawl4ai", "simple"]
    ] = Field("auto", description="Default Content Processing Engine for URLs")
    default_embedding_option: Optional[Literal["ask", "always", "never"]] = Field(
        "ask", description="Default Embedding Option for Vector Search"
    )
    auto_delete_files: Optional[Literal["yes", "no"]] = Field(
        "yes", description="Auto Delete Uploaded Files"
    )
    docling_ocr: Optional[bool] = Field(
        True,
        description=(
            "Run OCR on scanned PDFs and images when the Docling engine handles "
            "them. Disable for faster processing of text-native documents."
        ),
    )
    docling_formulas: Optional[bool] = Field(
        False,
        description=(
            "Extract mathematical formulas from documents when the Docling "
            "engine handles them. Slower to process."
        ),
    )
    docling_vision: Optional[bool] = Field(
        False,
        description=(
            "Enable vision-based enrichment (charts, images, diagrams) when "
            "the Docling engine handles them. Significantly slower and may "
            "call a vision model."
        ),
    )
    youtube_preferred_languages: Optional[List[str]] = Field(
        ["en", "pt", "es", "de", "nl", "en-GB", "fr", "de", "hi", "ja"],
        description="Preferred languages for YouTube transcripts",
    )
