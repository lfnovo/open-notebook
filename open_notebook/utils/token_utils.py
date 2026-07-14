"""
Token utilities for Open Notebook.
Handles token counting, cost calculations, and text chunking.
"""

import os
import re
from typing import List, Optional, Tuple

from open_notebook.config import TIKTOKEN_CACHE_DIR

# Set tiktoken cache directory before importing tiktoken to ensure
# tokenizer encodings are cached persistently in the data folder
os.environ["TIKTOKEN_CACHE_DIR"] = TIKTOKEN_CACHE_DIR

# Default context limit when it cannot be parsed from an error message.
# Used as the chunk size so each chunk fits within the default budget.
DEFAULT_CONTEXT_LIMIT = 8192

# Safety buffer: keep chunk content below the raw limit to leave room
# for the system prompt and output tokens.
SAFETY_BUFFER = 0.85

# Overlap between adjacent chunks in characters (≈1–2 sentences).
CHUNK_OVERLAP_CHARS = 200


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
        # disallowed_special=() treats sequences like "<|endoftext|>" as ordinary
        # text instead of raising ValueError. User/source content can legitimately
        # contain these substrings, and we only need a token count here.
        tokens = encoding.encode(input_string, disallowed_special=())
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


def parse_context_limit_error(error_str: str) -> Optional[Tuple[int, int]]:
    """
    Parse an LLM error string to extract the context limit and tokens sent.

    Supports Anthropic, OpenAI, Google/Gemini, and generic error formats.

    Each pattern explicitly identifies which captured group is the context
    limit vs tokens sent, rather than relying on a size heuristic (which
    is incorrect when the sent tokens outnumber the model's limit, as in
    Gemini's "X exceeded the limit of Y" format).

    Args:
        error_str: The raw error string from the LLM provider.

    Returns:
        (context_limit, tokens_sent) if both values can be parsed, else None.
    """
    # Each entry: (regex, limit_group_num, sent_group_num)
    #  1 — Anthropic: "your request was X tokens ... model's maximum is Y"
    #  2 — OpenAI:    "maximum context length is Y tokens ... you requested X"
    #  3 — Google:    "The number of tokens (X) exceeded the limit (Y)"
    #  4 — Generic:   "context_length_exceeded: X > Y"
    patterns: List[Tuple[str, int, int]] = [
        (
            r"(?:you have|sent|used|have|requested|your request was).*?"
            r"(\d+).*?(?:token|character).*?(?:maximum|limit|context).*?(\d+)",
            2,
            1,
        ),
        (
            r"(?:maximum|limit|context).*?(\d+).*?(?:token|character).*?"
            r"requested.*?(\d+)",
            1,
            2,
        ),
        (
            r"number of tokens.*?(\d+).*?exceeded.*?(\d+)",
            2,
            1,
        ),
        (
            r"context[_\s]length[_\s]exceeded.*?(\d+).*?(\d+)",
            2,
            1,
        ),
    ]
    for pattern, limit_group, sent_group in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            return (
                int(match.group(limit_group)),
                int(match.group(sent_group)),
            )
    return None


def chunk_text_by_tokens(
    text: str,
    max_chunk_tokens: int = int(DEFAULT_CONTEXT_LIMIT * SAFETY_BUFFER),
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> List[str]:
    """
    Split text into overlapping token-bounded chunks.

    Splits hierarchically: paragraphs first, then sentences, then word
    boundaries. Adds overlap_chars of trailing text from the previous
    chunk so context carries across chunk boundaries.

    Args:
        text: The text to split.
        max_chunk_tokens: Maximum tokens per chunk (default ~6963).
        overlap_chars: Characters of overlap from the previous chunk.

    Returns:
        A list of text chunks, each within the token budget.
        Returns [text] unchanged if it fits in a single chunk.
    """
    if token_count(text) <= max_chunk_tokens:
        return [text]

    # Split on paragraph boundaries first
    paragraphs = text.split("\n\n")
    raw_chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    def _flush() -> None:
        nonlocal current, current_tokens
        if current:
            raw_chunks.append("\n\n".join(current))
        current = []
        current_tokens = 0

    for para in paragraphs:
        para_tokens = token_count(para)
        if current_tokens + para_tokens > max_chunk_tokens and current:
            _flush()
        current.append(para)
        current_tokens += para_tokens
    _flush()

    # If any single paragraph exceeds max_chunk_tokens, split it further
    # by sentences, then by brute force.
    final_chunks: List[str] = []
    for chunk in raw_chunks:
        if token_count(chunk) <= max_chunk_tokens:
            final_chunks.append(chunk)
        else:
            # Split oversized chunk by sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", chunk)
            sentence_chunks: List[str] = []
            cur_sents: List[str] = []
            cur_sent_tokens = 0
            for sent in sentences:
                sent_tokens = token_count(sent)
                if cur_sent_tokens + sent_tokens > max_chunk_tokens and cur_sents:
                    sentence_chunks.append(" ".join(cur_sents))
                    cur_sents = []
                    cur_sent_tokens = 0
                cur_sents.append(sent)
                cur_sent_tokens += sent_tokens
            if cur_sents:
                sentence_chunks.append(" ".join(cur_sents))

            # Word-level fallback: if any sentence chunk still exceeds the
            # token budget (e.g. a run-on with no sentence boundaries), split
            # by whitespace word boundaries. This is the final brute-force
            # level after paragraph → sentence → word.
            word_chunks: List[str] = []
            for sc in sentence_chunks:
                if token_count(sc) <= max_chunk_tokens:
                    word_chunks.append(sc)
                else:
                    words = sc.split()
                    cur_words: List[str] = []
                    cur_word_tokens = 0
                    for w in words:
                        w_tokens = token_count(w)
                        if cur_word_tokens + w_tokens > max_chunk_tokens and cur_words:
                            word_chunks.append(" ".join(cur_words))
                            cur_words = []
                            cur_word_tokens = 0

                        # If a single word/string exceeds the token budget,
                        # split it at character boundaries as a last resort.
                        # This handles whitespace-free content (e.g. long
                        # base64/MD5 hashes, minified code, or CJK text
                        # without spaces) that no sentence/word split can
                        # break further.
                        if w_tokens > max_chunk_tokens:
                            if cur_words:
                                word_chunks.append(" ".join(cur_words))
                                cur_words = []
                                cur_word_tokens = 0
                            # Proportional character-level split.
                            # o200k ~0.75 tokens/char for English; we
                            # overshoot slightly and let the next stage
                            # of hierarchical splitting clean up.
                            n_chunks = max(1, w_tokens // max_chunk_tokens + 1)
                            chunk_len = max(1, len(w) // n_chunks)
                            for start in range(0, len(w), chunk_len):
                                piece = w[start : start + chunk_len]
                                word_chunks.append(piece)
                            continue

                        cur_words.append(w)
                        cur_word_tokens += w_tokens
                    if cur_words:
                        word_chunks.append(" ".join(cur_words))
            final_chunks.extend(word_chunks)

    # Add overlap from previous chunk and re-check token budget.
    # The overlap + continuation marker can push a chunk over
    # max_chunk_tokens; gracefully reduce the overlap when that happens.
    CONTINUATION_MARKER = "\n\n[... continuation from previous section ...]\n\n"

    result: List[str] = []
    for i, chunk in enumerate(final_chunks):
        if i > 0 and overlap_chars > 0:
            base_chunk = chunk  # preserve for retry below
            # Try progressively smaller overlap sizes
            chunk_upper_bound = max_chunk_tokens * 1.15
            for step_chars in [overlap_chars, overlap_chars // 2, overlap_chars // 4, 0]:
                overlap = final_chunks[i - 1][-step_chars:]
                chunk = overlap + CONTINUATION_MARKER + base_chunk
                if token_count(chunk) <= chunk_upper_bound:
                    break
                # If we hit zero overlap and still can't fit, accept the
                # over-budget chunk — it's close enough.
        result.append(chunk)

    return result
