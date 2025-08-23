"""
Utils package for Open Notebook.

To avoid circular imports, import functions directly:
- from open_notebook.utils.context_builder import ContextBuilder
- from open_notebook.utils import split_text, token_count
"""

from .text_utils import (
    split_text, 
    token_count, 
    remove_non_ascii, 
    remove_non_printable,
    parse_thinking_content,
    clean_thinking_content
)

__all__ = [
    "split_text", 
    "token_count", 
    "remove_non_ascii", 
    "remove_non_printable",
    "parse_thinking_content",
    "clean_thinking_content"
]