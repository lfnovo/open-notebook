"""
Token utilities for Open Notebook.
Handles token counting and cost calculations for language models.
"""

import os

from open_notebook.config import TIKTOKEN_CACHE_DIR

# Set tiktoken cache directory before importing tiktoken to ensure
# tokenizer encodings are cached persistently in the data folder
os.environ["TIKTOKEN_CACHE_DIR"] = TIKTOKEN_CACHE_DIR


def token_count(input_string: str) -> int:
    """
    Count the number of tokens in the input string using the 'o200k_base' encoding.

    Args:
        input_string (str): The input string to count tokens for.

    Returns:
        int: The number of tokens in the input string.
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("o200k_base")
        tokens = encoding.encode(input_string)
        return len(tokens)
    except ImportError:
        # Fallback: simple word count estimation
        return int(len(input_string.split()) * 1.3)


def token_cost(token_count: int, cost_per_million: float = 0.150) -> float:
    """
    Calculate the cost of tokens based on the token count and cost per million tokens.

    Args:
        token_count (int): The number of tokens.
        cost_per_million (float): The cost per million tokens. Default is 0.150.

    Returns:
        float: The calculated cost for the given token count.
    """
    return cost_per_million * (token_count / 1_000_000)


# --- Token-Aware Batching Utilities ---

import re
from typing import Iterator, List, Optional, Tuple

# Safety buffer when calculating batches (90% of limit)
SAFETY_BUFFER = 0.90

# Conservative fallback for unknown models
DEFAULT_CONTEXT_LIMIT = 8192

# Output token settings
DEFAULT_OUTPUT_TOKENS = 4096  # Initial output buffer for first attempt
OUTPUT_RATIO = 0.10  # 10% of context window reserved for output


def calculate_output_buffer(context_limit: int) -> int:
    """
    Calculate output buffer as percentage of context window.

    Args:
        context_limit: Model's context window size

    Returns:
        Output token limit (10% of context)
    """
    return int(context_limit * OUTPUT_RATIO)


def get_context_limit_from_error(
    error: Exception,
    default_limit: int = DEFAULT_CONTEXT_LIMIT,
) -> Tuple[Optional[int], int]:
    """
    Parse a context-limit error and return (tokens_sent, context_limit).

    This is a convenience wrapper around parse_context_limit_error() that handles
    the common pattern of falling back to a default limit when parsing fails.

    Args:
        error: The exception to parse
        default_limit: Fallback context limit if parsing fails (default: 8192)

    Returns:
        Tuple of (tokens_sent, context_limit) where:
        - tokens_sent may be None if only the limit was found in the error
        - context_limit is the parsed limit or default_limit if parsing failed
    """
    parsed = parse_context_limit_error(error)
    if parsed:
        return parsed
    return None, default_limit


def parse_context_limit_error(error: Exception) -> Optional[Tuple[int, int]]:
    """
    Parse context limit error to extract token counts.

    Attempts to extract:
    - The number of tokens that were sent
    - The model's context window limit

    Returns:
        Tuple of (tokens_sent, context_limit) if parseable, None otherwise

    Examples of error formats this handles:
    - "estimated number of input and maximum output tokens (144512) exceeded this model context window limit (128000)"
    - "context_length_exceeded: 144512 tokens > 128000 max"
    - "This model's maximum context length is 128000 tokens"
    """
    error_str = str(error)

    # Pattern 1: "tokens (X) exceeded...limit (Y)" or similar
    pattern1 = r"tokens?\s*\(?(\d+)\)?\s*(?:exceeded|>).*?(?:limit|max|maximum)[^\d]*(\d+)"
    match = re.search(pattern1, error_str, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Pattern 1b: "X tokens > Y max" format (numbers before labels)
    pattern1b = r"(\d+)\s*tokens?\s*(?:>|exceeded)\s*(\d+)\s*(?:max|limit)"
    match = re.search(pattern1b, error_str, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Pattern 2: "maximum context length is X tokens"
    pattern2 = r"(?:max|maximum)\s*(?:context)?\s*(?:length|limit|window)?\s*(?:is|of|:)?\s*(\d+)"
    match = re.search(pattern2, error_str, re.IGNORECASE)
    if match:
        return None, int(match.group(1))  # Only limit known

    # Pattern 3: Just look for large numbers that might be limits (common formats)
    # "128000 tokens" or "(128000)" near words like limit/max/context
    pattern3 = r"(?:context|limit|max|window)[^\d]*(\d{4,})"
    match = re.search(pattern3, error_str, re.IGNORECASE)
    if match:
        return None, int(match.group(1))

    return None


def is_context_limit_error(error: Exception) -> bool:
    """
    Check if error is a context/token limit error.

    Uses specific patterns to avoid false positives from rate limit errors
    or other unrelated errors containing words like "limit" or "exceeded".
    """
    error_str = str(error).lower()

    # Exclude rate limit errors explicitly
    if "rate limit" in error_str or "rate_limit" in error_str:
        return False

    # Specific context-limit indicators (phrases, not single words)
    context_indicators = [
        "context length",
        "context_length",
        "context limit",
        "context window",
        "token limit",
        "token_limit",
        "maximum context",
        "max context",
        "too many tokens",
        "tokens exceeded",
        "exceeded limit",  # "estimated tokens (X) exceeded limit (Y)"
        "input too long",
        "prompt too long",
        "exceeds the model",
        "exceeded this model",
    ]

    return any(ind in error_str for ind in context_indicators)


def batch_by_token_limit(texts: List[str], token_limit: int) -> Iterator[List[str]]:
    """
    Yield batches of texts fitting within token limit.

    Args:
        texts: List of text strings to batch
        token_limit: Maximum tokens per batch (safety buffer already applied)

    Yields:
        Lists of texts, each batch within token_limit

    Note: Oversized single texts are yielded alone (caller must handle).
    """
    if not texts:
        return

    batch, current_tokens = [], 0

    for text in texts:
        text_tokens = token_count(text)

        # Single text exceeds limit - yield alone
        if text_tokens > token_limit:
            if batch:
                yield batch
                batch, current_tokens = [], 0
            yield [text]
            continue

        # Adding would exceed limit - yield current batch first
        if current_tokens + text_tokens > token_limit and batch:
            yield batch
            batch, current_tokens = [], 0

        batch.append(text)
        current_tokens += text_tokens

    if batch:
        yield batch


def calculate_batch_token_limit(
    total_tokens: int, context_limit: int, num_texts: int
) -> int:
    """
    Calculate optimal batch token limit based on error info.

    Args:
        total_tokens: Total tokens that caused the error (or estimate)
        context_limit: Model's context window limit
        num_texts: Number of texts being embedded

    Returns:
        Token limit per batch with safety buffer
    """
    # Apply safety buffer to context limit
    safe_limit = int(context_limit * SAFETY_BUFFER)

    # If we know total tokens, calculate how many batches needed
    if total_tokens and total_tokens > safe_limit:
        num_batches = (total_tokens // safe_limit) + 1
        # Distribute evenly across batches
        tokens_per_batch = total_tokens // num_batches
        return int(tokens_per_batch * SAFETY_BUFFER)

    return safe_limit


def chunk_text_by_tokens(text: str, max_tokens: int) -> List[str]:
    """
    Split text into chunks that fit within the token limit.

    Uses paragraph boundaries when possible for cleaner splits,
    falling back to sentence boundaries for large paragraphs.

    Args:
        text: The text to split
        max_tokens: Maximum tokens per chunk

    Returns:
        List of text chunks, each within max_tokens
    """
    if token_count(text) <= max_tokens:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = token_count(para)

        # If single paragraph exceeds limit, split by sentences
        if para_tokens > max_tokens:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # Split large paragraph by sentences
            sentences = para.replace('. ', '.\n').split('\n')
            for sentence in sentences:
                sent_tokens = token_count(sentence)

                # Handle oversized sentences by splitting on whitespace
                if sent_tokens > max_tokens:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_tokens = 0

                    # Split long sentence into smaller pieces
                    words = sentence.split()
                    word_chunk: List[str] = []
                    word_tokens = 0
                    for word in words:
                        w_tokens = token_count(word)
                        if word_tokens + w_tokens > max_tokens and word_chunk:
                            chunks.append(' '.join(word_chunk))
                            word_chunk = []
                            word_tokens = 0
                        word_chunk.append(word)
                        word_tokens += w_tokens
                    # Finalize leftover words immediately to avoid mixing with paragraphs
                    if word_chunk:
                        chunks.append(' '.join(word_chunk))
                    continue

                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                current_chunk.append(sentence)
                current_tokens += sent_tokens
        elif current_tokens + para_tokens > max_tokens:
            # Start new chunk
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks
