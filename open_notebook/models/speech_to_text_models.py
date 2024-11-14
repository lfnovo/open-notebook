"""
Classes for supporting different transcription models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpeechToTextModel(ABC):
    """
    Abstract base class for speech to text models.
    """

    model_name: Optional[str] = None

    @abstractmethod
    def transcribe(self, audio_file_path: str) -> str:
        """
        Generates a text transcription from audio
        """
        raise NotImplementedError


@dataclass
class OpenAISpeechToTextModel(SpeechToTextModel):
    model_name: str

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes an audio file into text
        """
        from openai import OpenAI

        # todo: make this Singleton
        client = OpenAI()
        with open(audio_file_path, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                model=self.model_name, file=audio
            )
            return transcription.text


@dataclass
class GroqSpeechToTextModel(SpeechToTextModel):
    model_name: str

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes an audio file into text
        """
        from groq import Groq

        # todo: make this Singleton
        client = Groq()
        with open(audio_file_path, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                model=self.model_name, file=audio
            )
            return transcription.text
