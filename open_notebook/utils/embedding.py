"""
Unified embedding utilities for Open Notebook.

Provides centralized embedding generation with support for:
- Single text embedding (with automatic chunking and mean pooling for large texts)
- Batch text embedding (multiple texts with automatic batching)
- Mean pooling for combining multiple embeddings into one

All embedding operations in the application should use these functions
to ensure consistent behavior and proper handling of large content.

Environment Variables:
    OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE: Number of texts per embedding API call (default: 50).
        Different providers enforce different per-request limits; tune this when you hit
        HTTP 400/413 errors from your embedding provider.
"""

import asyncio
import os
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from loguru import logger

from .chunking import CHUNK_SIZE, ContentType, chunk_text

EMBEDDING_MAX_RETRIES = 3
EMBEDDING_RETRY_DELAY = 2  # seconds


def _get_embedding_batch_size() -> int:
    """Get embedding batch size from environment variable or use default.

    Different embedding providers enforce different limits on the number of
    texts that can be submitted in a single API call. Examples:
    - Mistral (mistral-embed): up to 512 inputs per request
    - OpenAI: up to 2048 inputs per request
    - Google: varies by model

    Returns:
        Batch size as a positive integer (default: 50)
    """
    batch_size_str = os.getenv("OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE")
    if batch_size_str:
        try:
            batch_size = int(batch_size_str)
            if batch_size < 1:
                logger.warning(
                    f"OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE ({batch_size}) must be at least 1. "
                    f"Using default value of 50."
                )
                return 50
            if batch_size > 512:
                logger.warning(
                    f"OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE ({batch_size}) is very large. "
                    f"This may exceed some embedding providers' per-request limits."
                )
            logger.info(f"Using custom embedding batch size: {batch_size}")
            return batch_size
        except ValueError:
            logger.warning(
                f"Invalid OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE value: '{batch_size_str}'. "
                f"Using default: 50"
            )
    return 50


EMBEDDING_BATCH_SIZE = _get_embedding_batch_size()

# Lazy import to avoid circular dependency:
# utils -> embedding -> models -> key_provider -> provider_config -> utils
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


async def generate_embeddings(
    texts: List[str], command_id: Optional[str] = None
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts with automatic batching and retry.

    Texts are split into batches of EMBEDDING_BATCH_SIZE to avoid exceeding
    provider payload limits. Each batch is retried up to EMBEDDING_MAX_RETRIES
    times on transient failures.

    Args:
        texts: List of text strings to embed
        command_id: Optional command ID for error logging context

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

    model_name = getattr(embedding_model, "model_name", "unknown")

    # Log text sizes for debugging
    text_sizes = [len(t) for t in texts]
    logger.debug(
        f"Generating embeddings for {len(texts)} texts "
        f"(sizes: min={min(text_sizes)}, max={max(text_sizes)}, "
        f"total={sum(text_sizes)} chars)"
    )

    all_embeddings: List[List[float]] = []
    total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * EMBEDDING_BATCH_SIZE
        end = start + EMBEDDING_BATCH_SIZE
        batch = texts[start:end]

        for attempt in range(1, EMBEDDING_MAX_RETRIES + 1):
            try:
                batch_embeddings = await embedding_model.aembed(batch)
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                cmd_context = f" (command: {command_id})" if command_id else ""
                if attempt < EMBEDDING_MAX_RETRIES:
                    logger.debug(
                        f"Embedding batch {batch_idx + 1}/{total_batches} "
                        f"attempt {attempt}/{EMBEDDING_MAX_RETRIES} failed "
                        f"using model '{model_name}'{cmd_context}: {e}. Retrying..."
                    )
                    await asyncio.sleep(EMBEDDING_RETRY_DELAY)
                else:
                    logger.debug(
                        f"Embedding batch {batch_idx + 1}/{total_batches} "
                        f"failed after {EMBEDDING_MAX_RETRIES} attempts "
                        f"using model '{model_name}'{cmd_context}: {e}"
                    )
                    raise RuntimeError(
                        f"Failed to generate embeddings using model '{model_name}' "
                        f"(batch {batch_idx + 1}/{total_batches}, "
                        f"{len(batch)} texts): {e}"
                    ) from e

    logger.debug(f"Generated {len(all_embeddings)} embeddings in {total_batches} batch(es)")
    return all_embeddings


async def generate_embedding(
    text: str,
    content_type: Optional[ContentType] = None,
    file_path: Optional[str] = None,
    command_id: Optional[str] = None,
) -> List[float]:
    """
    Generate a single embedding for text, handling large content via chunking and mean pooling.

    For short text (<= CHUNK_SIZE):
        - Embeds directly and returns the embedding

    For long text (> CHUNK_SIZE):
        - Chunks the text using appropriate splitter for content type
        - Embeds all chunks in batches
        - Combines embeddings via mean pooling

    Args:
        text: The text to embed
        content_type: Optional explicit content type for chunking
        file_path: Optional file path for content type detection
        command_id: Optional command ID for error logging context

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
        embeddings = await generate_embeddings([text], command_id=command_id)
        return embeddings[0]

    # Long text - chunk and mean pool
    logger.debug(f"Text exceeds chunk size ({len(text)} chars), chunking...")

    chunks = chunk_text(text, content_type=content_type, file_path=file_path)

    if not chunks:
        raise ValueError("Text chunking produced no chunks")

    if len(chunks) == 1:
        # Single chunk after splitting
        embeddings = await generate_embeddings(chunks, command_id=command_id)
        return embeddings[0]

    logger.debug(f"Embedding {len(chunks)} chunks and mean pooling")

    # Embed all chunks in batches
    embeddings = await generate_embeddings(chunks, command_id=command_id)

    # Mean pool to get single embedding
    pooled = await mean_pool_embeddings(embeddings)

    logger.debug(f"Mean pooled {len(embeddings)} embeddings into single vector")
    return pooled
