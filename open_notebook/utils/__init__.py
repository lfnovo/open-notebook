"""
Utils package for AgentBook.

To avoid circular imports, import functions directly:
- from agent_book.utils.context_builder import ContextBuilder
- from agent_book.utils import token_count, compare_versions
- from agent_book.utils.chunking import chunk_text, detect_content_type, ContentType
- from agent_book.utils.embedding import generate_embedding, generate_embeddings
- from agent_book.utils.encryption import encrypt_value, decrypt_value
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
]
