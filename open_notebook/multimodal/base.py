from abc import ABC, abstractmethod

from open_notebook.multimodal.types import (
    VideoUnderstandingInput,
    VideoUnderstandingResult,
)


class VideoUnderstandingProvider(ABC):
    """Abstract interface for provider-specific video understanding adapters."""

    @abstractmethod
    async def analyze(
        self, input_data: VideoUnderstandingInput
    ) -> VideoUnderstandingResult:
        """Analyze a video source and return a normalized result."""
