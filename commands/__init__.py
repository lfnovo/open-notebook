"""Surreal-commands integration for Open Notebook"""

from open_notebook.utils.logger_config import setup_logging

setup_logging()

from .embedding_commands import (
    embed_insight_command,
    embed_note_command,
    embed_source_command,
    rebuild_embeddings_command,
)
from .example_commands import analyze_data_command, process_text_command
from .external_api_commands import (
    external_output_generate_command,
    external_source_fetch_command,
    external_source_search_command,
)
from .kg_commands import extract_knowledge_graph_command
from .podcast_commands import generate_podcast_command
from .source_commands import process_source_command

__all__ = [
    # Embedding commands
    "embed_note_command",
    "embed_insight_command",
    "embed_source_command",
    "rebuild_embeddings_command",
    # Other commands
    "generate_podcast_command",
    "process_source_command",
    "extract_knowledge_graph_command",
    "external_source_search_command",
    "external_source_fetch_command",
    "external_output_generate_command",
    "process_text_command",
    "analyze_data_command",
]
