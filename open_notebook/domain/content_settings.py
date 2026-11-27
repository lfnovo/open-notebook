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
            "Extract mathematical formulas as structured markup when the Docling "
            "engine handles a document. Adds processing time."
        ),
    )
    docling_vision: Optional[bool] = Field(
        False,
        description=(
            "Describe images and charts using a vision model when the Docling "
            "engine handles a document. Significantly slower and may invoke a "
            "vision model."
        ),
    )
    # The vision endpoint fields map to content-core's docling_vision_* config.
    # Unset (None) leaves the CCORE_DOCLING_VISION_* worker variables in effect.
    # The API key is deliberately not stored here: settings are unencrypted, so
    # it stays in CCORE_DOCLING_VISION_API_KEY.
    docling_vision_url: Optional[str] = Field(
        None,
        description=(
            "OpenAI-compatible chat completions URL that Docling sends images to "
            "for description. Unset uses CCORE_DOCLING_VISION_URL."
        ),
    )
    docling_vision_model: Optional[str] = Field(
        None,
        description=(
            "Model name sent to the vision endpoint. Unset uses "
            "CCORE_DOCLING_VISION_MODEL."
        ),
    )
    docling_vision_prompt: Optional[str] = Field(
        None,
        description=(
            "Prompt for image descriptions. Unset uses CCORE_DOCLING_VISION_PROMPT "
            "or Docling's default prompt."
        ),
    )
    youtube_preferred_languages: Optional[List[str]] = Field(
        ["en", "pt", "es", "de", "nl", "en-GB", "fr", "hi", "ja", "zh-CN", "zh-TW"],
        description="Preferred languages for YouTube transcripts",
    )
