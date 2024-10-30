"""
Classes for supporting different embedding models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI


@dataclass
class EmbeddingModel(ABC):
    """
    Abstract base class for language models.
    """

    model_name: Optional[str] = None

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generates an embedding
        """
        raise NotImplementedError


@dataclass
class OpenAIEmbeddingModel(EmbeddingModel):
    model_name: str

    def embed(self, text: str) -> List[float]:
        """
        Embeds the content using Open AI embedding
        """
        # todo: make this Singleton
        client = OpenAI()
        text = text.replace("\n", " ")
        return (
            client.embeddings.create(input=[text], model=self.model_name)
            .data[0]
            .embedding
        )
