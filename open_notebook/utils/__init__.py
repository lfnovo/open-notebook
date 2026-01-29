"""
Utils package for Open Notebook.

To avoid circular imports, import functions directly:
- from open_notebook.utils.context_builder import ContextBuilder
- from open_notebook.utils import token_count, compare_versions
- from open_notebook.utils.chunking import chunk_text, detect_content_type, ContentType
- from open_notebook.utils.embedding import generate_embedding, generate_embeddings
- from open_notebook.utils.encryption import encrypt_value, decrypt_value, generate_key
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
from .encryption import (
    decrypt_value,
    encrypt_value,
    generate_key,
)
from .text_utils import (
    clean_thinking_content,
    parse_thinking_content,
    remove_non_ascii,
    remove_non_printable,
)
from .token_utils import token_cost, token_count
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
    "remove_non_ascii",
    "remove_non_printable",
    "parse_thinking_content",
    "clean_thinking_content",
    # Token utils
    "token_count",
    "token_cost",
    # Version utils
    "compare_versions",
    "get_installed_version",
    "get_version_from_github",
    # Encryption utils
    "decrypt_value",
    "encrypt_value",
    "generate_key",
]
