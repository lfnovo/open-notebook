import operator
from typing import List

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
from open_notebook.graphs.multipattern import graph as transform_graph
from open_notebook.utils import surreal_clean

# todo: we can make this more efficient


class SourceState(TypedDict):
    content_state: ContentState
    transformations: List[str]
    notebook_id: str
    source: Source
    transformations: Annotated[list, operator.add]


class TransformationState(TypedDict):
    source: Source
    transformation: dict


def content_process(state: SourceState):
    content_state = state["content_state"]
    logger.debug("Content processing started for new content")
    return {"content_state": content_graph.invoke(content_state)}


def run_patterns(input_text, patterns):
    output = transform_graph.invoke(dict(content_stack=[input_text], patterns=patterns))
    return output["output"]


def save_source(state: SourceState):
    logger.debug("Saving source")
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
    return {"source": source}


def trigger_transformations(state: SourceState, config: RunnableConfig):
    if len(state["transformations"]) == 0:
        return []
    transformations = Transformation.get_all()
    to_apply = [
        t
        for t in transformations["source_insights"]
        if t["name"] in state["transformations"]
    ]
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


def transform_content(state: TransformationState):
    source = state["source"]
    content = source.full_text
    transformation = state["transformation"]
    logger.debug(f"Applying transformation {transformation['name']}")
    result = run_patterns(content, patterns=transformation["patterns"])
    source.add_insight(transformation["name"], surreal_clean(result))
    return {"transformations": [{"name": transformation["name"], "content": result}]}


workflow = StateGraph(SourceState)
workflow.add_node("content_process", content_process)
workflow.add_node("save_source", save_source)
workflow.add_node("transform_content", transform_content)
workflow.add_edge(START, "content_process")
workflow.add_edge("content_process", "save_source")
workflow.add_conditional_edges(
    "save_source", trigger_transformations, ["transform_content"]
)
workflow.add_edge("transform_content", END)
source_graph = workflow.compile()