import operator
from typing import Annotated, List, Optional, Union

from ai_prompter import Prompter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from loguru import logger
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.utils.text_utils import clean_thinking_content
from open_notebook.utils.token_utils import (
    DEFAULT_CONTEXT_LIMIT,
    DEFAULT_OUTPUT_TOKENS,
    SAFETY_BUFFER,
    calculate_output_buffer,
    chunk_text_by_tokens,
    get_context_limit_from_error,
    is_context_limit_error,
    token_count,
)


class ChunkResult(TypedDict):
    """Result from processing a single chunk."""

    idx: int
    result: str


class TransformationState(TypedDict):
    """State for the transformation graph."""

    # Input fields
    input_text: str
    source: Source
    transformation: Transformation
    # Output field
    output: str
    # Chunking fields (populated when full content exceeds context limit)
    system_prompt: Optional[str]
    model_id: Optional[str]
    output_buffer: int
    chunks: Optional[List[str]]
    chunk_results: Annotated[list, operator.add]  # Collects parallel results
    needs_chunking: bool
    title: Optional[str]


class ChunkState(TypedDict):
    """State for processing a single chunk (used by Send)."""

    # Inherited from parent state
    system_prompt: str
    model_id: Optional[str]
    output_buffer: int
    title: str
    # Chunk-specific fields
    chunk: str
    chunk_idx: int
    total_chunks: int


def _get_source(state: dict) -> Optional[Source]:
    """Extract Source from state, handling type check."""
    source_obj = state.get("source")
    return source_obj if isinstance(source_obj, Source) else None


def _extract_response_content(response) -> str:
    """Extract and clean content from LLM response."""
    content = (
        response.content
        if isinstance(response.content, str)
        else str(response.content)
    )
    return clean_thinking_content(content)


def _build_system_prompt(state: dict) -> str:
    """Build the system prompt from transformation template."""
    transformation: Transformation = state["transformation"]
    transformation_template_text = transformation.prompt

    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        transformation_template_text = (
            f"{default_prompts.transformation_instructions}\n\n"
            f"{transformation_template_text}"
        )

    transformation_template_text = f"{transformation_template_text}\n\n# INPUT"

    return Prompter(template_text=transformation_template_text).render(data=state)


def _get_content(state: dict) -> str:
    """Extract content from state (input_text or source.full_text)."""
    content = state.get("input_text")
    if not content:
        source = _get_source(state)
        if source:
            content = source.full_text
    return str(content) if content else ""


async def try_full_content(state: dict, config: RunnableConfig) -> dict:
    """
    Try processing full content optimistically.

    On success: returns output and needs_chunking=False
    On context limit error: returns chunking parameters and needs_chunking=True
    """
    source = _get_source(state)
    content = _get_content(state)
    assert source or content, "No content to transform"

    transformation: Transformation = state["transformation"]
    title = transformation.title
    system_prompt = _build_system_prompt(state)
    output_buffer = DEFAULT_OUTPUT_TOKENS
    model_id = config.get("configurable", {}).get("model_id")

    payload = [SystemMessage(content=system_prompt), HumanMessage(content=content)]

    try:
        chain = await provision_langchain_model(
            str(payload),
            model_id,
            "transformation",
            max_tokens=output_buffer,
        )
        response = await chain.ainvoke(payload)
        cleaned_content = _extract_response_content(response)

        if source:
            await source.add_insight(title, cleaned_content)

        return {
            "output": cleaned_content,
            "needs_chunking": False,
        }

    except Exception as e:
        if not is_context_limit_error(e):
            raise

        # Parse error to get limit info
        tokens_sent, context_limit = get_context_limit_from_error(
            e, DEFAULT_CONTEXT_LIMIT
        )
        output_buffer = calculate_output_buffer(context_limit)

        if tokens_sent:
            logger.info(
                f"Transformation context limit error: {tokens_sent} tokens sent, "
                f"limit is {context_limit}. Will retry with parallel chunking."
            )
        else:
            logger.warning(
                f"Could not parse token count from error, using limit {context_limit}. "
                f"Content has ~{token_count(content)} tokens."
            )

        # Calculate chunk size based on context limit
        system_overhead = token_count(system_prompt)
        available_tokens = (
            int(context_limit * SAFETY_BUFFER) - system_overhead - output_buffer
        )
        chunk_size = max(available_tokens, 500)

        chunks = chunk_text_by_tokens(content, chunk_size)
        logger.info(
            f"Split content into {len(chunks)} chunks for parallel processing "
            f"of transformation '{title}'"
        )

        return {
            "needs_chunking": True,
            "system_prompt": system_prompt,
            "model_id": model_id,
            "output_buffer": output_buffer,
            "chunks": chunks,
            "chunk_results": [],
            "title": title,
        }


def fan_out_chunks(state: dict) -> Union[List[Send], str]:
    """
    Conditional edge function that fans out to process_chunk nodes in parallel.

    If needs_chunking is False, routes directly to synthesize (which handles both cases).
    If needs_chunking is True, sends each chunk to process_chunk in parallel.
    """
    if not state.get("needs_chunking", False):
        return "synthesize"

    chunks = state.get("chunks", [])
    if not chunks:
        return "synthesize"

    total_chunks = len(chunks)
    logger.info(f"Fanning out {total_chunks} chunks for parallel processing")

    return [
        Send(
            "process_chunk",
            {
                "system_prompt": state["system_prompt"],
                "model_id": state.get("model_id"),
                "output_buffer": state["output_buffer"],
                "title": state.get("title", ""),
                "chunk": chunk,
                "chunk_idx": idx,
                "total_chunks": total_chunks,
            },
        )
        for idx, chunk in enumerate(chunks)
    ]


async def process_chunk(state: ChunkState, config: RunnableConfig) -> dict:
    """
    Process a single chunk with the transformation.

    Runs in parallel with other chunks via LangGraph's Send API.
    Returns result that gets collected via operator.add into chunk_results.
    """
    idx = state["chunk_idx"]
    total = state["total_chunks"]
    title = state.get("title", "transformation")

    logger.info(f"Processing chunk {idx + 1}/{total} for '{title}'")

    payload = [
        SystemMessage(content=state["system_prompt"]),
        HumanMessage(
            content=f"[Processing section {idx + 1} of {total} from a larger document]\n\n{state['chunk']}"
        ),
    ]

    chain = await provision_langchain_model(
        str(payload),
        state.get("model_id"),
        "transformation",
        max_tokens=state["output_buffer"],
    )
    response = await chain.ainvoke(payload)

    return {"chunk_results": [{"idx": idx, "result": _extract_response_content(response)}]}


async def synthesize_results(state: dict, config: RunnableConfig) -> dict:
    """
    Synthesize chunk results into final output.

    If we already have an output (full content succeeded), returns early.
    If we have chunk_results, synthesizes them and saves insight.
    """
    source = _get_source(state)
    title = state.get("title") or state["transformation"].title

    # If full content succeeded, output is already set
    if state.get("output") and not state.get("needs_chunking", False):
        return {}

    chunk_results: List[ChunkResult] = state.get("chunk_results", [])
    if not chunk_results:
        logger.warning(f"No chunk results to synthesize for '{title}'")
        return {"output": ""}

    # Sort by index to ensure correct order
    sorted_results = sorted(chunk_results, key=lambda x: x["idx"])

    # Single chunk - no synthesis needed
    if len(sorted_results) == 1:
        result = sorted_results[0]["result"]
        logger.info(f"Successfully completed transformation '{title}' with single chunk")
        if source:
            await source.add_insight(title, result)
        return {"output": result}

    # Multiple chunks - synthesize
    logger.info(f"Synthesizing {len(sorted_results)} chunk results for '{title}'")

    combined_text = "\n\n---\n\n".join(
        f"## Result from Part {r['idx'] + 1}:\n{r['result']}" for r in sorted_results
    )

    synthesis_prompt = f"""You previously processed a large document in {len(sorted_results)} parts using the following instructions:

{state.get("system_prompt", "")}

Below are the results from each part. Your task is to synthesize these into a single, coherent output that combines the key information from all parts. Remove any redundancy and create a unified result.

Do NOT simply concatenate - intelligently merge and synthesize the information."""

    payload = [
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content=combined_text),
    ]

    chain = await provision_langchain_model(
        str(payload),
        state.get("model_id"),
        "transformation",
        max_tokens=state.get("output_buffer", DEFAULT_OUTPUT_TOKENS),
    )
    response = await chain.ainvoke(payload)
    result = _extract_response_content(response)

    logger.info(f"Successfully completed transformation '{title}' with parallel chunking")

    if source:
        await source.add_insight(title, result)

    return {"output": result}


# Build the graph
agent_state = StateGraph(TransformationState)

# Add nodes
agent_state.add_node("try_full", try_full_content)
agent_state.add_node("process_chunk", process_chunk)
agent_state.add_node("synthesize", synthesize_results)

# Add edges
agent_state.add_edge(START, "try_full")
agent_state.add_conditional_edges("try_full", fan_out_chunks, ["process_chunk", "synthesize"])
agent_state.add_edge("process_chunk", "synthesize")
agent_state.add_edge("synthesize", END)

graph = agent_state.compile()
