"""
Classes for supporting different embedding models
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import requests

# todo: add support for multiple embeddings (array)


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
class OllamaEmbeddingModel(EmbeddingModel):
    model_name: str
    base_url: str = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

    def embed(self, text: str) -> List[float]:
        """
        Embeds the content using Open AI embedding
        """
        text = text.replace("\n", " ")
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model_name, "input": [text]},
        )
        return response.json()["embeddings"][0]


@dataclass
class GeminiEmbeddingModel(EmbeddingModel):
    model_name: str

    def embed(self, text: str) -> List[float]:
        import google.generativeai as genai

        """
        Embeds the content using Open AI embedding
        """
        model_name = (
            self.model_name
            if self.model_name.startswith("models/")
            else f"models/{self.model_name}"
        )
        result = genai.embed_content(model=model_name, content=text)

        return result["embedding"]


@dataclass
class VertexEmbeddingModel(EmbeddingModel):
    model_name: str

    def embed(self, text: str) -> List[float]:
        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

        texts = [text]
        # The dimensionality of the output embeddings.
        # dimensionality = 256
        # The task type for embedding. Check the available tasks in the model's documentation.
        model = TextEmbeddingModel.from_pretrained(self.model_name)
        inputs = [TextEmbeddingInput(text) for text in texts]
        embeddings = model.get_embeddings(inputs)
        return embeddings[0].values


@dataclass
class OpenAIEmbeddingModel(EmbeddingModel):
    model_name: str

    def embed(self, text: str) -> List[float]:
        from openai import OpenAI

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
