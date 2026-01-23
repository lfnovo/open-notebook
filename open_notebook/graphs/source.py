import operator
from typing import Any, Dict, List, Optional

from content_core import extract_content
from content_core.common import ProcessSourceState
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import Annotated, TypedDict

from open_notebook.domain.content_settings import ContentSettings
from open_notebook.domain.models import Model, ModelManager
from open_notebook.domain.notebook import Asset, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.transformation import graph as transform_graph
from open_notebook.graphs.smol_docling_integration import (
    get_smol_docling_parser,
    check_smoldocling_available,
)


class SourceState(TypedDict):
    content_state: ProcessSourceState
    apply_transformations: List[Transformation]
    source_id: str
    notebook_ids: List[str]
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool


class TransformationState(TypedDict):
    source: Source
    transformation: Transformation


async def content_process(state: SourceState) -> dict:
    """
    Process source content using either content_core (default) or SmolDocling.
    
    The parser is selected based on ContentSettings.document_parser:
    - "content_core": Traditional extraction using content_core library
    - "smol_docling": VLM-based extraction using SmolDocling
    """
    # Load content settings from database
    try:
        content_settings = await ContentSettings.get_instance()  # type: ignore[assignment]
    except Exception:
        content_settings = ContentSettings(
            default_content_processing_engine_doc="auto",
            default_content_processing_engine_url="auto",
            default_embedding_option="ask",
            auto_delete_files="yes",
            youtube_preferred_languages=["en", "pt", "es", "de", "nl", "en-GB", "fr", "hi", "ja"]
        )
    
    content_state: Dict[str, Any] = state["content_state"]  # type: ignore[assignment]
    
    # Check if SmolDocling should be used for this content
    use_smol_docling = (
        content_settings.document_parser == "smol_docling" or
        content_settings.smol_docling_enabled
    )
    
    # SmolDocling is only applicable for PDF and image files
    file_path = content_state.get("file_path", "")
    is_pdf_or_image = (
        file_path and 
        file_path.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'))
    )
    
    if use_smol_docling and is_pdf_or_image and check_smoldocling_available():
        logger.info("=" * 60)
        logger.info(" SMOLDOCLING PARSER ACTIVATED ")
        logger.info(f"Processing file: {file_path}")
        logger.info("=" * 60)
        try:
            parser = get_smol_docling_parser(
                use_gpu=content_settings.smol_docling_use_gpu
            )
            result = await parser.parse_file(file_path)
            
            if result.success:
                # Update content_state with SmolDocling results
                content_state["content"] = result.content
                if result.title:
                    content_state["title"] = result.title
                content_state["source_type"] = "pdf" if file_path.lower().endswith('.pdf') else "image"
                logger.info("=" * 60)
                logger.info(f" SMOLDOCLING SUCCESS! Processed {result.page_count} pages")
                logger.info("=" * 60)
                return {"content_state": ProcessSourceState(**content_state)}
            else:
                logger.warning(f"SmolDocling parsing failed: {result.error_message}")
                logger.info("Falling back to content_core extraction")
        except Exception as e:
            logger.warning(f"SmolDocling error: {e}. Falling back to content_core")
    elif use_smol_docling and is_pdf_or_image and not check_smoldocling_available():
        logger.warning("SmolDocling is enabled but dependencies are not available. Using content_core.")
    
    # Default: use content_core for extraction
    content_state["url_engine"] = (
        content_settings.default_content_processing_engine_url or "auto"
    )
    content_state["document_engine"] = (
        content_settings.default_content_processing_engine_doc or "auto"
    )
    content_state["output_format"] = "markdown"

    # Add speech-to-text model configuration from Default Models
    try:
        model_manager = ModelManager()
        defaults = await model_manager.get_defaults()
        if defaults.default_speech_to_text_model:
            stt_model = await Model.get(defaults.default_speech_to_text_model)
            if stt_model:
                content_state["audio_provider"] = stt_model.provider
                content_state["audio_model"] = stt_model.name
                logger.debug(f"Using speech-to-text model: {stt_model.provider}/{stt_model.name}")
    except Exception as e:
        logger.warning(f"Failed to retrieve speech-to-text model configuration: {e}")
        # Continue without custom audio model (content-core will use its default)

    processed_state = await extract_content(content_state)
    return {"content_state": processed_state}


async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    # Get existing source using the provided source_id
    source = await Source.get(state["source_id"])
    if not source:
        raise ValueError(f"Source with ID {state['source_id']} not found")

    # Update the source with processed content
    source.asset = Asset(url=content_state.url, file_path=content_state.file_path)
    source.full_text = content_state.content
    
    # Preserve existing title if none provided in processed content
    if content_state.title:
        source.title = content_state.title
    
    await source.save()

    # NOTE: Notebook associations are created by the API immediately for UI responsiveness
    # No need to create them here to avoid duplicate edges

    if state["embed"]:
        logger.debug("Embedding content for vector search")
        await source.vectorize()

    return {"source": source}


def trigger_transformations(state: SourceState, config: RunnableConfig) -> List[Send]:
    if len(state["apply_transformations"]) == 0:
        return []

    to_apply = state["apply_transformations"]
    logger.debug(f"Applying transformations {to_apply}")

    return [
        Send(
            "transform_content",
            {
                "source": state["source"],
                "transformation": t,
            },
        )
        for t in to_apply
    ]


async def transform_content(state: TransformationState) -> Optional[dict]:
    source = state["source"]
    content = source.full_text
    if not content:
        return None
    transformation: Transformation = state["transformation"]

    logger.debug(f"Applying transformation {transformation.name}")
    result = await transform_graph.ainvoke(
        dict(input_text=content, transformation=transformation)  # type: ignore[arg-type]
    )
    await source.add_insight(transformation.title, result["output"])
    return {
        "transformation": [
            {
                "output": result["output"],
                "transformation_name": transformation.name,
            }
        ]
    }


# Create and compile the workflow
workflow = StateGraph(SourceState)

# Add nodes
workflow.add_node("content_process", content_process)
workflow.add_node("save_source", save_source)
workflow.add_node("transform_content", transform_content)
# Define the graph edges
workflow.add_edge(START, "content_process")
workflow.add_edge("content_process", "save_source")
workflow.add_conditional_edges(
    "save_source", trigger_transformations, ["transform_content"]
)
workflow.add_edge("transform_content", END)

# Compile the graph
source_graph = workflow.compile()
