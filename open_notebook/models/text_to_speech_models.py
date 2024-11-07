"""
Classes for supporting different text to speech models
"""

from abc import ABC
from dataclasses import dataclass
from typing import Optional


@dataclass
class TextToSpeechModel(ABC):
    """
    Abstract base class for text to speech models.
    """

    model_name: Optional[str] = None


@dataclass
class OpenAITextToSpeechModel(TextToSpeechModel):
    model_name: str


@dataclass
class ElevenLabsTextToSpeechModel(TextToSpeechModel):
    model_name: str


@dataclass
class GeminiTextToSpeechModel(TextToSpeechModel):
    model_name: str
