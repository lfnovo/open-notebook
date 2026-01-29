"""
Unified embedding utilities for Open Notebook.

Provides centralized embedding generation with support for:
- Single text embedding (with automatic chunking and mean pooling for large texts)
- Batch text embedding (multiple texts in a single API call)
- Mean pooling for combining multiple embeddings into one

All embedding operations in the application should use these functions
to ensure consistent behavior and proper handling of large content.
"""

from typing import TYPE_CHECKING, List, Optional

import numpy as np
from loguru import logger

from .chunking import CHUNK_SIZE, ContentType, chunk_text

# Lazy import to avoid circular dependency:
# utils -> embedding -> models -> key_provider -> api_key_config -> utils
if TYPE_CHECKING:
    from open_notebook.ai.models import ModelManager


async def mean_pool_embeddings(embeddings: List[List[float]]) -> List[float]:
    """
    Combine multiple embeddings into a single embedding using mean pooling.

    Algorithm:
    1. Normalize each embedding to unit length
    2. Compute element-wise mean
    3. Normalize the result to unit length

    This approach ensures the final embedding has the same properties as
    individual embeddings (unit length) regardless of input count.

    Args:
        embeddings: List of embedding vectors (each is a list of floats)

    Returns:
        Single embedding vector (mean pooled and normalized)

    Raises:
        ValueError: If embeddings list is empty or embeddings have different dimensions
    """
    if not embeddings:
        raise ValueError("Cannot mean pool empty list of embeddings")

    if len(embeddings) == 1:
        # Single embedding - just normalize and return
        arr = np.array(embeddings[0], dtype=np.float64)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    # Convert to numpy array
    arr = np.array(embeddings, dtype=np.float64)

    # Verify all embeddings have same dimension
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    # Normalize each embedding to unit length
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    # Avoid division by zero
    norms = np.where(norms > 0, norms, 1.0)
    normalized = arr / norms

    # Compute mean
    mean = np.mean(normalized, axis=0)

    # Normalize the result
    mean_norm = np.linalg.norm(mean)
    if mean_norm > 0:
        mean = mean / mean_norm

    return mean.tolist()


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call.

    This is more efficient than calling generate_embedding() multiple times
    when you have multiple texts to embed (e.g., source chunks).

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors, one per input text

    Raises:
        ValueError: If no embedding model is configured
        RuntimeError: If embedding generation fails
    """
    if not texts:
        return []

    # Lazy import to avoid circular dependency
    from open_notebook.ai.models import model_manager

    embedding_model = await model_manager.get_embedding_model()
    if not embedding_model:
        raise ValueError(
            "No embedding model configured. Please configure one in the Models section."
        )

    # Log text sizes for debugging
    text_sizes = [len(t) for t in texts]
    logger.debug(
        f"Generating embeddings for {len(texts)} texts "
        f"(sizes: min={min(text_sizes)}, max={max(text_sizes)}, "
        f"total={sum(text_sizes)} chars)"
    )

    try:
        # Single API call for all texts
        embeddings = await embedding_model.aembed(texts)
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings
    except Exception as e:
        logger.error(
            f"Failed to generate embeddings: {e} "
            f"(tried {len(texts)} texts, max size: {max(text_sizes)} chars)"
        )
        raise RuntimeError(f"Failed to generate embeddings: {e}") from e


async def generate_embedding(
    text: str,
    content_type: Optional[ContentType] = None,
    file_path: Optional[str] = None,
) -> List[float]:
    """
    Generate a single embedding for text, handling large content via chunking and mean pooling.

    For short text (<= CHUNK_SIZE):
        - Embeds directly and returns the embedding

    For long text (> CHUNK_SIZE):
        - Chunks the text using appropriate splitter for content type
        - Embeds all chunks in a single API call
        - Combines embeddings via mean pooling

    Args:
        text: The text to embed
        content_type: Optional explicit content type for chunking
        file_path: Optional file path for content type detection

    Returns:
        Single embedding vector (list of floats)

    Raises:
        ValueError: If text is empty or no embedding model configured
        RuntimeError: If embedding generation fails
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")

    text = text.strip()

    # Check if chunking is needed
    if len(text) <= CHUNK_SIZE:
        # Short text - embed directly
        logger.debug(f"Embedding short text ({len(text)} chars) directly")
        embeddings = await generate_embeddings([text])
        return embeddings[0]

    # Long text - chunk and mean pool
    logger.debug(f"Text exceeds chunk size ({len(text)} chars), chunking...")

    chunks = chunk_text(text, content_type=content_type, file_path=file_path)

    if not chunks:
        raise ValueError("Text chunking produced no chunks")

    if len(chunks) == 1:
        # Single chunk after splitting
        embeddings = await generate_embeddings(chunks)
        return embeddings[0]

    logger.debug(f"Embedding {len(chunks)} chunks and mean pooling")

    # Embed all chunks in single API call
    embeddings = await generate_embeddings(chunks)

    # Mean pool to get single embedding
    pooled = await mean_pool_embeddings(embeddings)

    logger.debug(f"Mean pooled {len(embeddings)} embeddings into single vector")
    return pooled
