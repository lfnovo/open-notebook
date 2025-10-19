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