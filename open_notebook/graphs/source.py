import operator
from typing import Any, Dict, List, Optional

from content_core.common import ProcessSourceState
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import Annotated, TypedDict

from open_notebook.content_extractors.service import ContentExtractionService
from open_notebook.domain.notebook import Asset, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.transformation import graph as transform_graph


class SourceState(TypedDict):
    content_state: ProcessSourceState
    apply_transformations: List[Transformation]
    source_id: str
    notebook_ids: List[str]
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool
    team_id: Optional[str]


class TransformationState(TypedDict):
    source: Source
    transformation: Transformation
    team_id: Optional[str]


async def content_process(state: SourceState) -> dict:
    content_state: Dict[str, Any] = state["content_state"]  # type: ignore[assignment]
    extraction_service = ContentExtractionService()

    logger.info(f"Starting content extraction for source_id={state.get('source_id')}")
    try:
        processed_state = await extraction_service.process(content_state)
        logger.info(f"Content extraction completed for source_id={state.get('source_id')}")
        logger.debug(f"Extracted content length: {len(processed_state.content or '')} characters")
    except Exception as e:
        logger.error(f"Error during content extraction for source_id={state.get('source_id')}: {e}")
        raise

    if not processed_state.content or not processed_state.content.strip():
        url = processed_state.url or ""
        if url and ("youtube.com" in url or "youtu.be" in url):
            raise ValueError(
                "Could not extract content from this YouTube video. "
                "No transcript or subtitles are available. "
                "Try configuring a Speech-to-Text model in Settings "
                "to transcribe the audio instead."
            )
        raise ValueError(
            "Could not extract any text content from this source. "
            "The content may be empty, inaccessible, or in an unsupported format."
        )

    return {"content_state": processed_state}


async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    # Get existing source using the provided source_id
    source = await Source.get(state["source_id"])
    if not source:
        raise ValueError(f"Source with ID {state['source_id']} not found")

    # Update the source with processed content
    source.asset = Asset(
        url=content_state.url,
        file_path=content_state.file_path,
        external_source_name=source.asset.external_source_name if source.asset else None,
    )
    source.full_text = content_state.content

    # Preserve user-set title; only overwrite placeholder or empty titles
    if content_state.title and (not source.title or source.title == "Processing..."):
        source.title = content_state.title

    await source.save()

    # NOTE: Notebook associations are created by the API immediately for UI responsiveness
    # No need to create them here to avoid duplicate edges

    if state["embed"]:
        if source.full_text and source.full_text.strip():
            logger.debug("Embedding content for vector search")
            await source.vectorize(team_id=state.get("team_id"))
        else:
            logger.warning(
                f"Source {source.id} has no text content to embed, skipping vectorization"
            )

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
                "team_id": state.get("team_id"),
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

    logger.info(f"Submitting background job for transformation {transformation.name}")
    from commands.lifecycle import submit_command_job

    await submit_command_job(
        "open_notebook",
        "run_transformation",
            {
                "source_id": str(source.id),
                "transformation_id": str(transformation.id),
                "team_id": state.get("team_id"),
            },
        ensure_registered=False,
    )

    return {
        "transformation": [
            {
                "output": "Transformation job submitted to background worker",
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
