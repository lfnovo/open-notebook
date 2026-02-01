"""
Utils package for Open Notebook.

To avoid circular imports, import functions directly:
- from open_notebook.utils.context_builder import ContextBuilder
- from open_notebook.utils import token_count, compare_versions
- from open_notebook.utils.chunking import chunk_text, detect_content_type, ContentType
- from open_notebook.utils.embedding import generate_embedding, generate_embeddings
"""

from .chunking import (
    CHUNK_SIZE,
    ContentType,
    chunk_text,
    detect_content_type,
    detect_content_type_from_extension,
    detect_content_type_from_heuristics,
)
from .embedding import (
    generate_embedding,
    generate_embeddings,
    mean_pool_embeddings,
)
from .text_utils import (
    clean_thinking_content,
    parse_thinking_content,
    remove_non_ascii,
    remove_non_printable,
)
from .token_utils import (
    DEFAULT_CONTEXT_LIMIT,
    SAFETY_BUFFER,
    batch_by_token_limit,
    calculate_batch_token_limit,
    chunk_text_by_tokens,
    get_context_limit_from_error,
    is_context_limit_error,
    parse_context_limit_error,
    token_cost,
    token_count,
)
from .version_utils import (
    compare_versions,
    get_installed_version,
    get_version_from_github,
)

__all__ = [
    # Chunking
    "CHUNK_SIZE",
    "ContentType",
    "chunk_text",
    "detect_content_type",
    "detect_content_type_from_extension",
    "detect_content_type_from_heuristics",
    # Embedding
    "generate_embedding",
    "generate_embeddings",
    "mean_pool_embeddings",
    # Text utils
    "clean_thinking_content",
    "parse_thinking_content",
    "remove_non_ascii",
    "remove_non_printable",
    # Token utils
    "DEFAULT_CONTEXT_LIMIT",
    "SAFETY_BUFFER",
    "batch_by_token_limit",
    "calculate_batch_token_limit",
    "chunk_text_by_tokens",
    "get_context_limit_from_error",
    "is_context_limit_error",
    "parse_context_limit_error",
    "token_cost",
    "token_count",
    # Version utils
    "compare_versions",
    "get_installed_version",
    "get_version_from_github",
]
