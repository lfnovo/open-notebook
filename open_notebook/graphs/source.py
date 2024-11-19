import operator
from typing import List, Optional

from langchain_core.runnables import (
    RunnableConfig,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import Annotated, TypedDict

from open_notebook.domain.notebook import Asset, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.content_processing import ContentState
from open_notebook.graphs.content_processing import graph as content_graph
from open_notebook.graphs.transformation import graph as transform_graph
from open_notebook.utils import surreal_clean


class SourceState(TypedDict):
    content_state: ContentState
    apply_transformations: List[Transformation]
    notebook_id: str
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool


class TransformationState(TypedDict):
    source: Source
    transformation: Transformation


async def content_process(state: SourceState) -> dict:
    content_state = state["content_state"]
    logger.info("Content processing started for new content")
    processed_state = await content_graph.ainvoke(content_state)
    return {"content_state": processed_state}


def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    source = Source(
        asset=Asset(
            url=content_state.get("url"), file_path=content_state.get("file_path")
        ),
        full_text=surreal_clean(content_state["content"]),
        title=content_state.get("title"),
    )
    source.save()

    if state["notebook_id"]:
        logger.debug(f"Adding source to notebook {state['notebook_id']}")
        source.add_to_notebook(state["notebook_id"])

    if state["embed"]:
        logger.debug("Embedding content for vector search")
        source.vectorize()

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
        dict(input_text=content, transformation=transformation)
    )
    source.add_insight(transformation.title, surreal_clean(result["output"]))
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
