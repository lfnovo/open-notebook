from typing import ClassVar, Dict, List, Literal, Optional

import os

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
    provider_credentials: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Stored provider environment variables keyed by env var name",
    )

    def apply_provider_credentials(self) -> None:
        """Apply stored provider credentials to process environment variables."""
        for env_key, value in (self.provider_credentials or {}).items():
            if not env_key:
                continue

            normalized_key = env_key.strip()
            if not normalized_key:
                continue

            if value:
                os.environ[normalized_key] = value
            else:
                os.environ.pop(normalized_key, None)
