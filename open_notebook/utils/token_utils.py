"""
Token utilities for Open Notebook.
Handles token counting, cost calculations, context-limit error parsing, and
text chunking for working within model context windows.
"""

import os
import re
from typing import List, Optional, Tuple

from open_notebook.config import TIKTOKEN_CACHE_DIR

# Set tiktoken cache directory before importing tiktoken to ensure
# tokenizer encodings are cached persistently in the data folder
os.environ["TIKTOKEN_CACHE_DIR"] = TIKTOKEN_CACHE_DIR

# Safety buffer: use 90% of the context limit to leave headroom for output and
# for tokenizer disagreement between our estimate and the provider's.
SAFETY_BUFFER = 0.90

# Conservative fallback context limit (tokens) when an error can't be parsed.
DEFAULT_CONTEXT_LIMIT = 8192

# Initial output buffer (tokens). Matches the max_tokens the transformation
# graph has always used for the full-content attempt; lowering it would
# silently truncate outputs on the common (non-chunked) path.
DEFAULT_OUTPUT_TOKENS = 8192

# Fraction of the context window reserved for the model's output.
OUTPUT_RATIO = 0.10


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
    except (ImportError, OSError) as e:
        # Fallback: handles ImportError (tiktoken not installed) AND network/OS
        # errors such as urllib.error.URLError or ConnectionError raised in
        # offline environments when the encoding file cannot be downloaded.
        from loguru import logger

        logger.warning(
            "tiktoken unavailable, falling back to word-count estimation: {}", e
        )
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


def parse_context_limit_error(error: Exception) -> Optional[Tuple[int, int]]:
    """Extract token counts from a context-limit error message.

    Context-limit detection is inherently provider-format-dependent: providers
    report the limit only in free-text error messages, so this parses the known
    wordings and will return ``None`` for formats it doesn't recognize (callers
    then fall back to ``DEFAULT_CONTEXT_LIMIT`` — see
    ``get_context_limit_from_error``). Supported formats:

    - OpenAI: ``"maximum context length is 8192 tokens... 10000 tokens"``
    - Anthropic: ``"prompt is too long: 10000 tokens > 8192 maximum"``
    - Google: ``"input token count (10000) exceeds the maximum (8192)"``
    - Generic variants: ``"10000 tokens > 8192"``, ``"tokens (10000) exceeded
      ... limit 8192"``, or a lone ``"max/maximum ... <limit>"``

    Returns:
        ``(tokens_sent, context_limit)`` if parseable, else ``None``.
        ``tokens_sent`` may be ``None`` if only the limit could be found.
    """
    error_str = str(error) if error else ""
    if not error_str:
        return None

    match = re.search(
        r"tokens?\s*\(?(\d+)\)?\s*(?:exceeded|>).*?(?:limit|max|maximum)[^\d]*(\d+)",
        error_str,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(
        r"(\d+)\s*tokens?\s*(?:>|exceeded)\s*(\d+)\s*(?:max|limit)",
        error_str,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    # OpenAI: "maximum context length is 8192 tokens...10000 tokens"
    match = re.search(
        r"maximum context length is (\d+) tokens.*?(\d+) tokens",
        error_str,
        re.DOTALL,
    )
    if match:
        return int(match.group(2)), int(match.group(1))

    # Anthropic: "prompt is too long: 10000 tokens > 8192 maximum"
    match = re.search(
        r"prompt is too long: (\d+) tokens? > (\d+) maximum", error_str
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    # Google: "input token count (10000) exceeds the maximum (8192)"
    match = re.search(
        r"input token count \((\d+)\) exceeds the maximum \((\d+)\)", error_str
    )
    if match:
        return int(match.group(1)), int(match.group(2))

    # Generic: "10000 tokens > 8192"
    match = re.search(r"(\d+)\s*tokens?\s*>\s*(\d+)", error_str)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Only the limit is known.
    match = re.search(
        r"(?:max|maximum)\s*(?:context)?\s*(?:length|limit|window)?\s*(?:is|of|:)?\s*(\d+)",
        error_str,
        re.IGNORECASE,
    )
    if match:
        return None, int(match.group(1))

    match = re.search(
        r"(?:context|limit|max|window)[^\d]*(\d{4,})", error_str, re.IGNORECASE
    )
    if match:
        return None, int(match.group(1))

    return None


def is_context_limit_error(error: Exception) -> bool:
    """Return True if the exception is a context/token-limit error (and not a
    rate limit, auth, quota, network, etc.).

    Like ``parse_context_limit_error``, this matches provider wordings by
    keyword: non-context errors are excluded first, then context keywords are
    required. Unknown wordings return False, so callers treat the error as a
    regular failure rather than chunking on it."""
    error_msg = str(error).lower()

    non_context_keywords = [
        "rate limit",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "quota exceeded",
        "unauthorized",
        "authentication",
        "forbidden",
        "not found",
        "invalid api key",
        "billing",
        "insufficient_quota",
        "server error",
        "internal error",
        "timeout",
        "connection",
    ]
    for keyword in non_context_keywords:
        if keyword in error_msg:
            return False

    context_keywords = [
        "maximum context length",
        "token limit",
        "too many tokens",
        "prompt is too long",
        "exceeds the maximum",
        "context window",
        "max_tokens",
        "token count",
        "context length",
        "input too long",
        "request too large",
        "payload size exceeds",
        "you requested",
    ]
    for keyword in context_keywords:
        if keyword in error_msg:
            return True

    return False


def get_context_limit_from_error(
    error: Exception, default_limit: int = DEFAULT_CONTEXT_LIMIT
) -> Tuple[Optional[int], int]:
    """Parse a context-limit error, falling back to ``default_limit`` when the
    limit can't be parsed. Returns ``(tokens_sent, context_limit)``.

    The fallback is deliberately conservative: an unrecognized wording yields
    ``DEFAULT_CONTEXT_LIMIT`` (8192), which may over-chunk a large-context
    model (more, smaller chunks) but never produces chunks that are too big to
    process."""
    parsed = parse_context_limit_error(error)
    if parsed:
        return parsed
    return None, default_limit


def calculate_output_buffer(context_limit: int) -> int:
    """Reserve a slice of the context window for the model's output."""
    return int(context_limit * OUTPUT_RATIO)


def chunk_text_by_tokens(text: str, max_tokens: int) -> List[str]:
    """Split text into chunks that each fit within ``max_tokens``.

    Hierarchical: paragraphs, then sentences, then words, then a hard character
    split as a last resort.
    """
    if not text:
        return []
    if token_count(text) <= max_tokens:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    if len(paragraphs) > 1:
        chunks = _merge_splits(paragraphs, max_tokens)
        if chunks:
            return chunks

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 1:
        chunks = _merge_splits(sentences, max_tokens)
        if chunks:
            return chunks

    chunks = _merge_splits(text.split(), max_tokens, separator=" ")
    if chunks:
        return chunks

    # Last resort: hard split (rough estimate 1 token ~= 4 chars).
    char_limit = max_tokens * 4
    return [text[i : i + char_limit] for i in range(0, len(text), char_limit)]


def _merge_splits(
    parts: List[str], max_tokens: int, separator: str = "\n\n"
) -> List[str]:
    """Merge split parts into chunks respecting the token limit, recursing into
    finer splits for any single part that's still too large."""
    chunks: List[str] = []
    current_chunk = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if token_count(part) > max_tokens:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            if separator == "\n\n":
                sub_chunks = _merge_splits(
                    re.split(r"(?<=[.!?])\s+", part), max_tokens, " "
                )
            elif separator == " ":
                char_limit = max_tokens * 4
                sub_chunks = [
                    part[i : i + char_limit]
                    for i in range(0, len(part), char_limit)
                ]
            else:
                sub_chunks = [part]
            chunks.extend(sub_chunks)
            continue

        candidate = f"{current_chunk}{separator}{part}" if current_chunk else part
        if token_count(candidate) <= max_tokens:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
