"""
Classes for supporting different language and vector models
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_vertexai import ChatVertexAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_ollama.chat_models import ChatOllama
from langchain_openai.chat_models import ChatOpenAI

# from redisvl.utils.vectorize import BaseVectorizer
# from redisvl.utils.vectorize.text.openai import OpenAITextVectorizer


@dataclass
class LanguageModel(ABC):
    """
    Abstract base class for language models.
    """

    model_name: Optional[str] = None
    max_tokens: Optional[int] = 850
    temperature: Optional[float] = 1.0
    streaming: bool = True
    top_p: Optional[float] = 0.9
    kwargs: Dict[str, Any] = field(default_factory=dict)
    json: bool = False

    @abstractmethod
    def to_langchain(self) -> BaseChatModel:
        """
        Convert the language model to a LangChain chat model.
        """
        raise NotImplementedError


@dataclass
class OllamaLanguageModel(LanguageModel):
    """
    Language model that uses the Ollama chat model.
    """

    model_name: str
    base_url: str = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    max_tokens: Optional[int] = 650
    json: bool = False

    def to_langchain(self) -> ChatOllama:
        """
        Convert the language model to a LangChain chat model.
        """
        return ChatOllama(
            # api_key="ollama",
            model=self.model_name,
            base_url=self.base_url,
            # keep_alive="10m",
            num_predict=self.max_tokens,
            temperature=self.temperature,
            verbose=True,
            top_p=self.top_p,
        )


@dataclass
class VertexAnthropicLanguageModel(LanguageModel):
    """
    Language model that uses the Vertex Anthropic chat model.
    """

    model_name: str
    project: Optional[str] = os.environ.get("VERTEX_PROJECT", "no-project")
    location: Optional[str] = os.environ.get("VERTEX_LOCATION", "us-central1")

    def to_langchain(self) -> ChatAnthropicVertex:
        """
        Convert the language model to a LangChain chat model.
        """
        return ChatAnthropicVertex(
            model=self.model_name,
            project=self.project,
            location=self.location,
            max_tokens=self.max_tokens,
            streaming=False,
            kwargs=self.kwargs,
            top_p=self.top_p,
        )


@dataclass
class LiteLLMLanguageModel(LanguageModel):
    """
    Language model that uses the LiteLLM chat model.
    """

    model_name: str

    def to_langchain(self) -> ChatLiteLLM:
        """
        Convert the language model to a LangChain chat model.
        """
        return ChatLiteLLM(
            model=self.model_name,
            temperature=self.temperature or 0.5,
            max_tokens=self.max_tokens,
            streaming=self.streaming,
            top_p=self.top_p,
        )


@dataclass
class VertexAILanguageModel(LanguageModel):
    """
    Language model that uses the Vertex AI chat model.
    """

    model_name: str
    project: Optional[str] = os.environ.get("VERTEX_PROJECT", "no-project")
    location: Optional[str] = os.environ.get("VERTEX_LOCATION", "us-central1")

    def to_langchain(self) -> ChatVertexAI:
        """
        Convert the language model to a LangChain chat model.
        """
        return ChatVertexAI(
            model=self.model_name,
            streaming=self.streaming,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            location=self.location,
            project=self.project,
            safety_settings=None,
            api_key="AIzaSyCt4zB5eZVZPh7WRxIh9oY_rwblP6BOyWE",
        )


@dataclass
class OpenRouterLanguageModel(LanguageModel):
    """
    Language model that uses the OpenAI chat model.
    """

    model_name: str

    def to_langchain(self) -> ChatOpenAI:
        """
        Convert the language model to a LangChain chat model.
        """
        kwargs = self.kwargs
        if self.json:
            kwargs["response_format"] = {"type": "json_object"}

        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature or 0.5,
            base_url=os.environ.get(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            max_tokens=self.max_tokens,
            model_kwargs=kwargs,
            streaming=self.streaming,
            api_key=os.environ.get("OPENROUTER_API_KEY", "openrouter"),
            top_p=self.top_p,
        )


@dataclass
class AnthropicLanguageModel(LanguageModel):
    """
    Language model that uses the Anthropic chat model.
    """

    model_name: str

    def to_langchain(self) -> ChatAnthropic:
        """
        Convert the language model to a LangChain chat model.
        """
        return ChatAnthropic(  # type: ignore[call-arg]
            model_name=self.model_name,
            max_tokens_to_sample=self.max_tokens or 850,
            model_kwargs=self.kwargs,
            streaming=False,
            timeout=30,
            top_p=self.top_p,
        )


@dataclass
class OpenAILanguageModel(LanguageModel):
    """
    Language model that uses the OpenAI chat model.
    """

    model_name: str

    def to_langchain(self) -> ChatOpenAI:
        """
        Convert the language model to a LangChain chat model.
        """
        kwargs = self.kwargs
        if self.json:
            kwargs["response_format"] = {"type": "json_object"}

        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature or 0.5,
            max_tokens=self.max_tokens,
            model_kwargs=kwargs,
            streaming=self.streaming,
            top_p=self.top_p,
        )


# @dataclass
# class EmbeddingModel(ABC):
#     model_name: str
#     dimensions: int

#     def to_redis_vectorizer(self) -> BaseVectorizer:
#         raise NotImplementedError


# @dataclass
# class OpenAIEmbeddingModel(EmbeddingModel):
#     """
#     Embedding model that uses the OpenAI text embedding model.
#     """

#     model_name: str
#     dimensions: int

#     def to_redis_vectorizer(self) -> OpenAITextVectorizer:
#         """
#         Convert the embedding model to a Redis vectorizer.
#         """
#         return OpenAITextVectorizer(model=self.model_name)
