import os
from typing import Any, Dict

import magic
from langgraph.graph import END, START, StateGraph
from loguru import logger

from open_notebook.exceptions import UnsupportedTypeException
from open_notebook.graphs.content_processing.audio import extract_audio
from open_notebook.graphs.content_processing.office import (
    SUPPORTED_OFFICE_TYPES,
    extract_office_content,
)
from open_notebook.graphs.content_processing.pdf import (
    SUPPORTED_FITZ_TYPES,
    extract_pdf,
)
from open_notebook.graphs.content_processing.state import ContentState
from open_notebook.graphs.content_processing.text import extract_txt
from open_notebook.graphs.content_processing.url import extract_url, url_provider
from open_notebook.graphs.content_processing.video import extract_best_audio_from_video
from open_notebook.graphs.content_processing.youtube import extract_youtube_transcript


async def source_identification(state: ContentState) -> Dict[str, str]:
    """
    Identify the content source based on parameters
    """
    if state.get("content"):
        doc_type = "text"
    elif state.get("file_path"):
        doc_type = "file"
    elif state.get("url"):
        doc_type = "url"
    else:
        raise ValueError("No source provided.")

    return {"source_type": doc_type}


async def file_type(state: ContentState) -> Dict[str, Any]:
    """
    Identify the file using python-magic
    """
    return_dict = {}
    file_path = state.get("file_path")
    if file_path is not None:
        return_dict["identified_type"] = magic.from_file(file_path, mime=True)
        return_dict["title"] = os.path.basename(file_path)
    return return_dict


async def file_type_edge(data: ContentState) -> str:
    assert data.get("identified_type"), "Type not identified"
    identified_type = data["identified_type"]

    if identified_type == "text/plain":
        return "extract_txt"
    elif identified_type in SUPPORTED_FITZ_TYPES:
        return "extract_pdf"
    elif identified_type in SUPPORTED_OFFICE_TYPES:
        return "extract_office_content"
    elif identified_type.startswith("video"):
        return "extract_best_audio_from_video"
    elif identified_type.startswith("audio"):
        return "extract_audio"
    else:
        raise UnsupportedTypeException(
            f"Unsupported file type: {data.get('identified_type')}"
        )


async def delete_file(data: ContentState) -> Dict[str, Any]:
    if data.get("delete_source"):
        logger.debug(f"Deleting file: {data.get('file_path')}")
        file_path = data.get("file_path")
        if file_path is not None:
            try:
                os.remove(file_path)
                return {"file_path": None}
            except FileNotFoundError:
                logger.warning(f"File not found while trying to delete: {file_path}")
    else:
        logger.debug("Not deleting file")
    return {}


async def url_type_router(x: ContentState) -> str:
    return x.get("identified_type", "")


async def source_type_router(x: ContentState) -> str:
    return x.get("source_type", "")


# Create workflow
workflow = StateGraph(ContentState)

# Add nodes
workflow.add_node("source", source_identification)
workflow.add_node("url_provider", url_provider)
workflow.add_node("file_type", file_type)
workflow.add_node("extract_txt", extract_txt)
workflow.add_node("extract_pdf", extract_pdf)
workflow.add_node("extract_url", extract_url)
workflow.add_node("extract_office_content", extract_office_content)
workflow.add_node("extract_best_audio_from_video", extract_best_audio_from_video)
workflow.add_node("extract_audio", extract_audio)
workflow.add_node("extract_youtube_transcript", extract_youtube_transcript)
workflow.add_node("delete_file", delete_file)

# Add edges
workflow.add_edge(START, "source")
workflow.add_conditional_edges(
    "source",
    source_type_router,
    {
        "url": "url_provider",
        "file": "file_type",
        "text": END,
    },
)
workflow.add_conditional_edges(
    "file_type",
    file_type_edge,
)
workflow.add_conditional_edges(
    "url_provider",
    url_type_router,
    {"article": "extract_url", "youtube": "extract_youtube_transcript"},
)
workflow.add_edge("url_provider", END)
workflow.add_edge("file_type", END)
workflow.add_edge("extract_url", END)
workflow.add_edge("extract_txt", END)
workflow.add_edge("extract_youtube_transcript", END)

workflow.add_edge("extract_pdf", "delete_file")
workflow.add_edge("extract_office_content", "delete_file")
workflow.add_edge("extract_best_audio_from_video", "extract_audio")
workflow.add_edge("extract_audio", "delete_file")
workflow.add_edge("delete_file", END)

# Compile graph
graph = workflow.compile()
