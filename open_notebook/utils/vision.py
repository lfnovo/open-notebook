"""Vision processing utilities for image and video analysis."""
import base64
import mimetypes
from pathlib import Path
from typing import Tuple

from langchain_core.messages import HumanMessage
from loguru import logger


async def encode_image_base64(file_path: str) -> Tuple[str, str]:
    """
    Encode image file to base64 with MIME type detection.

    Args:
        file_path: Path to the image file

    Returns:
        Tuple of (base64_data, mime_type)
    """
    path = Path(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Default to PNG if we can't detect
        mime_type = "image/png"

    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    logger.debug(f"Encoded image {file_path} as {mime_type} ({len(data)} chars)")
    return data, mime_type


async def analyze_image(
    file_path: str,
    model,  # LangChain-compatible model
    prompt: str = "Describe this image in detail.",
) -> str:
    """
    Analyze a single image using a vision model.

    Args:
        file_path: Path to the image file
        model: LangChain-compatible vision model (from .to_langchain())
        prompt: The prompt to send with the image

    Returns:
        String description/analysis of the image
    """
    data, mime_type = await encode_image_base64(file_path)

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{data}"},
            },
            {"type": "text", "text": prompt},
        ]
    )

    logger.debug(f"Analyzing image {file_path} with prompt: {prompt[:50]}...")
    response = await model.ainvoke([message])
    return response.content


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS timestamp string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string (e.g., "01:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
