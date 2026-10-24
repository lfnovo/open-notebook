"""
Unified embedding utilities for Open Notebook.

Provides centralized embedding generation with support for:
- Single text embedding (with automatic chunking and mean pooling for large texts)
- Batch text embedding (multiple texts with automatic batching)
- Mean pooling for combining multiple embeddings into one

All embedding operations in the application should use these functions
to ensure consistent behavior and proper handling of large content.
"""

import asyncio
import hashlib
import os
from typing import Dict, List, Optional

import numpy as np
from loguru import logger

from .chunking import CHUNK_SIZE, ContentType, chunk_text
from .token_utils import token_count


def _get_embedding_batch_size() -> int:
    """
    Read the embedding batch size from the environment.

    This is intentionally configurable because provider limits vary widely, and
    CPU-only local embedding endpoints often need smaller batches than cloud APIs.
    """
    raw = os.getenv("OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE", "50").strip()
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
        return value
    except ValueError:
        logger.warning(
            "Invalid OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE='{}'; falling back to 50",
            raw,
        )
        return 50


EMBEDDING_BATCH_SIZE = _get_embedding_batch_size()
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_RETRY_DELAY = 2  # seconds

DEFAULT_EMBEDDING_CACHE_MAX_ROWS = 5000


def _get_embedding_cache_max_rows() -> int:
    """Read the embedding cache row limit from the environment (0 disables)."""
    name = "OPEN_NOTEBOOK_EMBEDDING_CACHE_MAX_ROWS"
    raw = os.getenv(name, str(DEFAULT_EMBEDDING_CACHE_MAX_ROWS)).strip()
    try:
        value = int(raw)
        if value < 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning(
            "Invalid {}={}; falling back to {}",
            name,
            raw,
            DEFAULT_EMBEDDING_CACHE_MAX_ROWS,
        )
        return DEFAULT_EMBEDDING_CACHE_MAX_ROWS


EMBEDDING_CACHE_MAX_ROWS = _get_embedding_cache_max_rows()


def _embedding_cache_key(model_name: str, text: str) -> str:
    """Return the sha256 hex digest of the model name and the text."""
    return hashlib.sha256(f"{model_name}\x00{text}".encode("utf-8")).hexdigest()


async def _cache_lookup(hashes: List[str]) -> Dict[str, List[float]]:
    """Return cached embeddings keyed by hash; empty on any cache failure."""
    from open_notebook.database.repository import repo_query

    try:
        rows = await repo_query(
            "SELECT hash, embedding FROM embedding_cache WHERE hash IN $hashes",
            {"hashes": hashes},
        )
        return {row["hash"]: row["embedding"] for row in rows}
    except Exception as e:
        logger.warning(f"Embedding cache lookup failed: {e}")
        return {}


async def _cache_store(model_name: str, entries: Dict[str, List[float]]) -> None:
    """Save new embeddings to the cache; failures are logged and ignored."""
    from open_notebook.database.repository import repo_insert

    if not entries:
        return
    try:
        await repo_insert(
            "embedding_cache",
            [
                {"hash": h, "model": model_name, "embedding": e}
                for h, e in entries.items()
            ],
            ignore_duplicates=True,
        )
    except Exception as e:
        logger.warning(f"Embedding cache write failed: {e}")


async def _cache_evict(max_rows: int) -> None:
    """Delete the oldest cache rows when the table exceeds max_rows."""
    from open_notebook.database.repository import ensure_record_id, repo_query

    try:
        counted = await repo_query("SELECT count() AS n FROM embedding_cache GROUP ALL")
        excess = (counted[0]["n"] if counted else 0) - max_rows
        if excess <= 0:
            return
        oldest = await repo_query(
            "SELECT id, created FROM embedding_cache ORDER BY created ASC LIMIT $n",
            {"n": excess},
        )
        await repo_query(
            "DELETE embedding_cache WHERE id IN $ids",
            {"ids": [ensure_record_id(row["id"]) for row in oldest]},
        )
        logger.info(f"Evicted {len(oldest)} oldest embedding cache rows")
    except Exception as e:
        logger.warning(f"Embedding cache eviction failed: {e}")


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
    texts: List[str], command_id: Optional[str] = None, use_cache: bool = False
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts with automatic batching and retry.

    Texts are split into batches of EMBEDDING_BATCH_SIZE to avoid exceeding
    provider payload limits. Each batch is retried up to EMBEDDING_MAX_RETRIES
    times on transient failures.

    Args:
        texts: List of text strings to embed
        command_id: Optional command ID for error logging context
        use_cache: If True, reuse cached embeddings keyed by model name and
            chunk text, and store new ones, so a retried call only sends the
            missing chunks to the provider. Defaults to False (no cache
            reads or writes). Has no effect when
            OPEN_NOTEBOOK_EMBEDDING_CACHE_MAX_ROWS is 0.

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
    metrics: tuple[int, int, int, int] | None = None

    def _get_size_metrics() -> tuple[int, int, int, int]:
        nonlocal metrics
        if metrics is None:
            token_sizes = [token_count(t) for t in texts]
            metrics = (
                min(token_sizes),
                max(token_sizes),
                sum(token_sizes),
                sum(len(t) for t in texts),
            )
        return metrics

    logger.opt(lazy=True).debug(
        "Generating embeddings for {} texts "
        "(tokens: min={}, max={}, total={}; chars: total={})",
        lambda: len(texts),
        lambda: _get_size_metrics()[0],
        lambda: _get_size_metrics()[1],
        lambda: _get_size_metrics()[2],
        lambda: _get_size_metrics()[3],
    )

    all_embeddings: List[List[float]] = []
    cache_on = use_cache and EMBEDDING_CACHE_MAX_ROWS > 0 and model_name != "unknown"
    total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * EMBEDDING_BATCH_SIZE
        end = start + EMBEDDING_BATCH_SIZE
        full_batch = texts[start:end]
        hashes = [_embedding_cache_key(model_name, t) for t in full_batch]
        cached = await _cache_lookup(hashes) if cache_on else {}
        miss_hashes = [h for h in hashes if h not in cached]
        batch = [t for t, h in zip(full_batch, hashes) if h in miss_hashes]
        new_embeddings: List[List[float]] = []
        if cache_on:
            logger.info(
                f"Embedding batch {batch_idx + 1}/{total_batches}: "
                f"{len(full_batch) - len(batch)} cache hits, {len(batch)} misses"
            )

        for attempt in range(1, EMBEDDING_MAX_RETRIES + 1) if batch else ():
            try:
                new_embeddings = await embedding_model.aembed(batch)
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
                    if cache_on:
                        await _cache_evict(EMBEDDING_CACHE_MAX_ROWS)
                    raise RuntimeError(
                        f"Failed to generate embeddings using model '{model_name}' "
                        f"(batch {batch_idx + 1}/{total_batches}, "
                        f"{len(batch)} texts): {e}"
                    ) from e

        if cache_on and len(new_embeddings) != len(batch):
            raise ValueError(
                f"Embedding count mismatch in batch {batch_idx + 1}/{total_batches}: "
                f"got {len(new_embeddings)} embeddings for {len(batch)} texts"
            )

        if cached:
            fresh = iter(new_embeddings)
            all_embeddings.extend(
                cached[h] if h in cached else next(fresh) for h in hashes
            )
        else:
            all_embeddings.extend(new_embeddings)
        if cache_on:
            await _cache_store(model_name, dict(zip(miss_hashes, new_embeddings)))

    if cache_on:
        await _cache_evict(EMBEDDING_CACHE_MAX_ROWS)

    logger.debug(
        f"Generated {len(all_embeddings)} embeddings in {total_batches} batch(es)"
    )
    return all_embeddings


async def generate_embedding(
    text: str,
    content_type: Optional[ContentType] = None,
    file_path: Optional[str] = None,
    command_id: Optional[str] = None,
) -> List[float]:
    """
    Generate a single embedding for text, handling large content via chunking and mean pooling.

    For short text (<= CHUNK_SIZE tokens):
        - Embeds directly and returns the embedding

    For long text (> CHUNK_SIZE tokens):
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
    text_tokens = token_count(text)

    # Check if chunking is needed
    if text_tokens <= CHUNK_SIZE:
        # Short text - embed directly
        logger.debug(f"Embedding short text ({text_tokens} tokens) directly")
        embeddings = await generate_embeddings([text], command_id=command_id)
        return embeddings[0]

    # Long text - chunk and mean pool
    logger.debug(f"Text exceeds chunk size ({text_tokens} tokens), chunking...")

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
