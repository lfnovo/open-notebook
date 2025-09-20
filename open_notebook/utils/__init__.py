"""
Utils package for Open Notebook.

To avoid circular imports, import functions directly:
- from open_notebook.utils.context_builder import ContextBuilder
- from open_notebook.utils import split_text, token_count, compare_versions
"""

from .text_utils import (
    clean_thinking_content,
    parse_thinking_content,
    remove_non_ascii,
    remove_non_printable,
    split_text,
)
from .token_utils import token_cost, token_count
from .version_utils import (
    compare_versions,
    get_installed_version,
    get_version_from_github,
)

__all__ = [
    "split_text",
    "remove_non_ascii",
    "remove_non_printable",
    "parse_thinking_content",
    "clean_thinking_content",
    "token_count",
    "token_cost",
    "compare_versions",
    "get_installed_version",
    "get_version_from_github"
]