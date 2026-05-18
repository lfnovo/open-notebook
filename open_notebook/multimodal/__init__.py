"""Provider-neutral multimodal capability interfaces."""

from open_notebook.multimodal.base import VideoUnderstandingProvider
from open_notebook.multimodal.types import (
    VideoEntity,
    VideoTimelineSegment,
    VideoUnderstandingInput,
    VideoUnderstandingResult,
)

__all__ = [
    "VideoUnderstandingProvider",
    "VideoEntity",
    "VideoTimelineSegment",
    "VideoUnderstandingInput",
    "VideoUnderstandingResult",
]
