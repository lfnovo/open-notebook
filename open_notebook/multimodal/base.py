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

    async def test_connection(self) -> tuple[bool, str]:
        """
        Validate provider connectivity for Settings model tests.

        Providers should override this when they can perform a lightweight
        authenticated request without requiring a real video input.
        """
        raise NotImplementedError("Connection testing is not implemented")
