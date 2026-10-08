"""Validated inline images shared by both chat APIs and their checkpoints."""

import base64
import binascii
import warnings
from io import BytesIO
from typing import Any, Literal
from uuid import uuid4

from langchain_core.messages import HumanMessage
from PIL import Image, UnidentifiedImageError
from pydantic import (
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

MAX_CHAT_IMAGES = 4
MAX_CHAT_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
_MAX_DATA_URL_LENGTH = 4 * ((MAX_CHAT_IMAGE_BYTES + 2) // 3) + 32
_IMAGE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}


class ChatImage(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    data_url: str = Field(max_length=_MAX_DATA_URL_LENGTH, repr=False)

    kind: Literal["generated", "source"] | None = None
    source_id: str | None = None
    source_title: str | None = None
    page: int | None = Field(default=None, ge=1)

    @model_serializer(mode="wrap")
    def serialize_image(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        return {key: value for key, value in handler(self).items() if value is not None}

    @field_validator("name")
    @classmethod
    def filename_only(cls, value: str) -> str:
        return value.replace("\\", "/").rsplit("/", 1)[-1] or "image"

    @field_validator("data_url")
    @classmethod
    def validate_image(cls, value: str) -> str:
        header, separator, encoded = value.partition(",")
        mime = header.removeprefix("data:").removesuffix(";base64")
        if (
            not separator
            or header != f"data:{mime};base64"
            or mime not in _IMAGE_FORMATS
        ):
            raise ValueError("Chat images must be inline PNG, JPEG or WebP images.")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid image encoding.") from exc
        if not raw or len(raw) > MAX_CHAT_IMAGE_BYTES:
            raise ValueError("Each chat image must be no larger than 5 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    if image.format != _IMAGE_FORMATS[mime]:
                        raise ValueError(
                            "Image content does not match its declared format."
                        )
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError(
                            "Chat images must be no larger than 25 megapixels."
                        )
                    image.verify()
        except (
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise ValueError("The image is invalid or too large to decode.") from exc
        return value


class ChatInput(BaseModel):
    message: str = ""
    images: list[ChatImage] = Field(default_factory=list, max_length=MAX_CHAT_IMAGES)
    model_override: str | None = None
    visual_tools: bool = False

    @model_validator(mode="after")
    def require_content(self) -> "ChatInput":
        if not self.message.strip() and not self.images:
            raise ValueError("A message or at least one image is required.")
        return self


def build_user_message(message: str, images: list[ChatImage]) -> HumanMessage:
    if not images:
        return HumanMessage(content=message, id=str(uuid4()))
    blocks: list[str | dict[Any, Any]] = []
    if message.strip():
        blocks.append({"type": "text", "text": message})
    blocks.extend(
        {"type": "image_url", "image_url": {"url": image.data_url}} for image in images
    )
    return HumanMessage(
        content=blocks,
        id=str(uuid4()),
        additional_kwargs={"image_names": [image.name for image in images]},
    )


def message_images(message: Any) -> list[ChatImage]:
    response_images = getattr(message, "additional_kwargs", {}).get(
        "response_images", []
    )
    if response_images and getattr(message, "type", None) == "ai":
        return [ChatImage.model_construct(**image) for image in response_images]
    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return []
    names = getattr(message, "additional_kwargs", {}).get("image_names", [])
    images: list[ChatImage] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "image_url":
            url = block.get("image_url", {}).get("url", "")
            if url.startswith("data:"):
                index = len(images)
                # Checkpoint images were validated at ingestion. Avoid decoding
                # every historical image again whenever a session is read.
                images.append(
                    ChatImage.model_construct(
                        name=names[index]
                        if index < len(names)
                        else f"image-{index + 1}",
                        data_url=url,
                    )
                )
    return images


def chat_model_context(messages: list) -> str:
    """Count text and a conservative image allowance, never base64 as tokens.

    Tokenizing image bytes can spuriously switch to a large-context model and
    adds considerable latency. Providers perform their own image tokenization.
    """
    from open_notebook.utils.text_utils import extract_text_content

    parts = []
    for message in messages:
        parts.append(f"{message.type}: {extract_text_content(message.content)}")
        content = message.content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") in {
                    "image_url",
                    "image",
                }:
                    parts.append(" image" * 2048)
    return "\n".join(parts)
