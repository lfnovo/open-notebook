"""
Unified embedding utilities for Open Notebook.

Provides centralized embedding generation with support for:
- Single text embedding (with automatic chunking and mean pooling for large texts)
- Batch text embedding (multiple texts in a single API call)
- Mean pooling for combining multiple embeddings into one

All embedding operations in the application should use these functions
to ensure consistent behavior and proper handling of large content.
"""

from typing import List, Optional

import numpy as np
from loguru import logger

from open_notebook.ai.models import model_manager

from .chunking import CHUNK_SIZE, ContentType, chunk_text
from .token_utils import (
    DEFAULT_CONTEXT_LIMIT,
    SAFETY_BUFFER,
    batch_by_token_limit,
    calculate_batch_token_limit,
    get_context_limit_from_error,
    is_context_limit_error,
    parse_context_limit_error,
    token_count,
)


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
    Generate embeddings with automatic retry and batching on context errors.

    Strategy:
    1. Try embedding all texts in one call (optimistic)
    2. On context limit error, parse the limit from the error
    3. Re-batch based on extracted limit and retry

    Args:
        texts: List of text strings to embed
        command_id: Optional command ID for error logging context

    Returns:
        List of embedding vectors, one per input text

    Raises:
        ValueError: If no embedding model configured
        RuntimeError: If embedding fails after retries
    """
    if not texts:
        return []

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

    # Optimistic: try all at once
    try:
        embeddings = await embedding_model.aembed(texts)
        logger.debug(f"Generated {len(embeddings)} embeddings in single batch")
        return embeddings
    except Exception as e:
        cmd_context = f" (command: {command_id})" if command_id else ""

        if not is_context_limit_error(e):
            # Log at debug level - the calling command will log at appropriate level
            logger.debug(
                f"Embedding API error using model '{model_name}' "
                f"for {len(texts)} texts (sizes: {min(text_sizes)}-{max(text_sizes)} chars)"
                f"{cmd_context}: {e}"
            )
            raise RuntimeError(
                f"Failed to generate embeddings using model '{model_name}': {e}"
            ) from e

        # Parse error to get limit info using centralized helper
        tokens_sent, context_limit = get_context_limit_from_error(e, DEFAULT_CONTEXT_LIMIT)
        if tokens_sent:
            logger.info(
                f"Context limit error using model '{model_name}'{cmd_context}: "
                f"{tokens_sent} tokens sent, limit is {context_limit}. Retrying with batching."
            )
        else:
            tokens_sent = sum(token_count(t) for t in texts)
            logger.warning(
                f"Could not parse token count from error{cmd_context}, using limit {context_limit}. "
                f"Estimated {tokens_sent} tokens in {len(texts)} texts."
            )

        # Calculate batch size
        if not tokens_sent:
            tokens_sent = sum(token_count(t) for t in texts)

        batch_limit = calculate_batch_token_limit(
            tokens_sent, context_limit, len(texts)
        )
        logger.info(f"Batching with token limit {batch_limit}")

        # Retry with batching
        return await _generate_embeddings_batched(
            embedding_model, texts, batch_limit
        )


async def _generate_embeddings_batched(
    model, texts: List[str], token_limit: int
) -> List[List[float]]:
    """Generate embeddings in batches with adaptive retry."""
    all_embeddings = []

    for i, batch in enumerate(batch_by_token_limit(texts, token_limit)):
        logger.debug(f"Processing batch {i+1}: {len(batch)} texts")
        try:
            batch_embeddings = await _embed_with_adaptive_retry(
                model, batch, token_limit
            )
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"Batch {i+1} failed: {e}")
            raise RuntimeError(f"Failed to embed batch {i+1}: {e}") from e

    logger.debug(f"Generated {len(all_embeddings)} embeddings in batches")
    return all_embeddings


async def _embed_with_adaptive_retry(
    model, texts: List[str], token_limit: int, max_splits: int = 3
) -> List[List[float]]:
    """
    Embed texts with adaptive splitting on context errors.

    If a batch still fails, splits in half and retries recursively.
    """
    try:
        return await model.aembed(texts)
    except Exception as e:
        if not is_context_limit_error(e) or len(texts) == 1 or max_splits <= 0:
            raise

        # Try to parse a more specific limit from this error
        parsed = parse_context_limit_error(e)
        if parsed and parsed[1]:
            new_limit = int(parsed[1] * SAFETY_BUFFER)
            if new_limit < token_limit:
                token_limit = new_limit
                logger.info(f"Adjusted batch limit to {token_limit} from error")

        logger.warning(
            f"Batch of {len(texts)} texts still too large, "
            f"splitting (retries left: {max_splits})"
        )

        mid = len(texts) // 2
        first = await _embed_with_adaptive_retry(
            model, texts[:mid], token_limit, max_splits - 1
        )
        second = await _embed_with_adaptive_retry(
            model, texts[mid:], token_limit, max_splits - 1
        )
        return first + second


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
        - Embeds all chunks in a single API call
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

    # Embed all chunks in single API call
    embeddings = await generate_embeddings(chunks, command_id=command_id)

    # Mean pool to get single embedding
    pooled = await mean_pool_embeddings(embeddings)

    logger.debug(f"Mean pooled {len(embeddings)} embeddings into single vector")
    return pooled
