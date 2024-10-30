"""
Classes for supporting different transcription models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from open_notebook.domain.models import Model


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
        # todo: make this Singleton
        client = OpenAI()
        with open(audio_file_path, "rb") as audio:
            transcription = client.audio.transcriptions.create(
                model=self.model_name, file=audio
            )
            return transcription.text


SPEECH_TO_TEXT_CLASS_MAP = {
    "openai": OpenAISpeechToTextModel,
}


# todo: acho que dá pra juntar todos os get models em uma coisa só
def get_speech_to_text_model(model_id):
    assert model_id, "Model ID cannot be empty"
    model = Model.get(model_id)
    if not model:
        raise ValueError(f"Model with ID {model_id} not found")
    if model.provider not in SPEECH_TO_TEXT_CLASS_MAP.keys():
        raise ValueError(
            f"Provider {model.provider} not compatible with Embedding Models"
        )
    return SPEECH_TO_TEXT_CLASS_MAP[model.provider](model_name=model.name)
