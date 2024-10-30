"""
Classes for supporting different embedding models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from open_notebook.domain.models import Model


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


EMBEDDING_CLASS_MAP = {
    "openai": OpenAIEmbeddingModel,
}


def get_embedding_model(model_id):
    assert model_id, "Model ID cannot be empty"
    model = Model.get(model_id)
    if not model:
        raise ValueError(f"Model with ID {model_id} not found")
    if model.provider not in EMBEDDING_CLASS_MAP.keys():
        raise ValueError(
            f"Provider {model.provider} not compatible with Embedding Models"
        )
    return EMBEDDING_CLASS_MAP[model.provider](model_name=model.name)
