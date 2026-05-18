from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VideoUnderstandingInput(BaseModel):
    source_id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    transcript_markdown: Optional[str] = None


class VideoTimelineSegment(BaseModel):
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    title: Optional[str] = None
    description: str


class VideoEntity(BaseModel):
    name: str
    entity_type: Optional[str] = None
    description: Optional[str] = None


class VideoUnderstandingResult(BaseModel):
    summary: str
    timeline: List[VideoTimelineSegment] = Field(default_factory=list)
    entities: List[VideoEntity] = Field(default_factory=list)
    key_events: List[str] = Field(default_factory=list)
    transcript_used: bool = False
    provider: str
    model: str
    raw_response: Optional[Dict[str, Any]] = None
