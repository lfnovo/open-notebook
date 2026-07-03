"""Transformation graph with large-document support.

Runs a transformation over a source/text. It first tries the full content
optimistically; if the model's context window is exceeded, it splits the content
into token-sized chunks, processes them in parallel, and synthesizes the partial
results back into a single output.

The synthesis is itself reduced **hierarchically**: combining many chunk results
into one call can exceed the context window too (each result is up to
``output_buffer`` tokens, and there can be many chunks), so results are batched
to fit a token budget and synthesized in rounds until one result remains.
"""

import asyncio
import operator
import weakref
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
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content
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

# Bound how many chunk/synthesis LLM calls run at once so a large document (many
# chunks) doesn't fan out into a burst of provider requests. Note this is a
# second concurrency layer on top of the worker's own task limit
# (OPEN_NOTEBOOK_WORKER_MAX_TASKS, see #893): the worst-case number of
# concurrent provider calls is roughly worker tasks x this limit.
_CHUNK_CONCURRENCY_LIMIT = 3

# Semaphores are created lazily per event loop: an asyncio.Semaphore binds to
# the loop it is first awaited from, and this graph runs from both the worker's
# and the API's loops. All Send() nodes of one invocation share a loop, so a
# per-loop semaphore still bounds the fan-out of a single transformation.
_chunk_semaphores: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = (
    weakref.WeakKeyDictionary()
)


def _get_chunk_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    sem = _chunk_semaphores.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(_CHUNK_CONCURRENCY_LIMIT)
        _chunk_semaphores[loop] = sem
    return sem


class ChunkResult(TypedDict):
    """Result from processing a single chunk."""

    idx: int
    result: str


class TransformationState(TypedDict, total=False):
    """State for the transformation graph.

    ``input_text``/``source``/``transformation``/``output`` are the public
    fields; the rest are populated only when the content exceeds the context
    window and the graph falls back to chunking.
    """

    input_text: str
    source: Source
    transformation: Transformation
    output: str
    # Chunking fields (populated when full content exceeds the context limit)
    system_prompt: Optional[str]
    model_id: Optional[str]
    output_buffer: int
    context_limit: Optional[int]
    chunks: Optional[List[str]]
    chunk_results: Annotated[list, operator.add]  # collects parallel results
    needs_chunking: bool
    title: Optional[str]


class ChunkState(TypedDict):
    """State for processing a single chunk (used by Send)."""

    system_prompt: str
    model_id: Optional[str]
    output_buffer: int
    title: str
    chunk: str
    chunk_idx: int
    total_chunks: int


def _get_source(state: dict) -> Optional[Source]:
    source_obj = state.get("source")
    return source_obj if isinstance(source_obj, Source) else None


def _extract_response_content(response) -> str:
    return clean_thinking_content(extract_text_content(response.content))


def _build_system_prompt(state: dict) -> str:
    transformation: Transformation = state["transformation"]
    template_text = transformation.prompt
    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        template_text = (
            f"{default_prompts.transformation_instructions}\n\n{template_text}"
        )
    return Prompter(template_text=template_text).render(data=state)


def _get_content(state: dict) -> str:
    content = state.get("input_text")
    if not content:
        source = _get_source(state)
        if source:
            content = source.full_text
    return str(content) if content else ""


async def try_full_content(state: dict, config: RunnableConfig) -> dict:
    """Try processing the full content; on a context-limit error, fall back to
    chunking by returning chunking parameters and ``needs_chunking=True``."""
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
            str(payload), model_id, "transformation", max_tokens=output_buffer
        )
        response = await chain.ainvoke(payload)
        cleaned_content = _extract_response_content(response)

        if source:
            await source.add_insight(title, cleaned_content)

        return {"output": cleaned_content, "needs_chunking": False}

    except OpenNotebookError:
        raise
    except Exception as e:
        if not is_context_limit_error(e):
            error_class, user_message = classify_error(e)
            raise error_class(user_message) from e

        tokens_sent, context_limit = get_context_limit_from_error(
            e, DEFAULT_CONTEXT_LIMIT
        )
        output_buffer = calculate_output_buffer(context_limit)
        logger.info(
            f"Transformation '{title}' exceeded context "
            f"({tokens_sent or '?'} tokens > {context_limit}); chunking."
        )

        system_overhead = token_count(system_prompt)
        available = int(context_limit * SAFETY_BUFFER) - system_overhead - output_buffer
        chunk_size = max(available, 500)
        chunks = chunk_text_by_tokens(content, chunk_size)
        logger.info(f"Split content into {len(chunks)} chunks for '{title}'")

        return {
            "needs_chunking": True,
            "system_prompt": system_prompt,
            "model_id": model_id,
            "output_buffer": output_buffer,
            "context_limit": context_limit,
            "chunks": chunks,
            "chunk_results": [],
            "title": title,
        }


def fan_out_chunks(state: dict) -> Union[List[Send], str]:
    """Conditional edge: fan out chunks to parallel ``process_chunk`` nodes, or
    route straight to ``synthesize`` when no chunking is needed."""
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
    """Process a single chunk (runs in parallel via LangGraph's Send API)."""
    idx = state["chunk_idx"]
    total = state["total_chunks"]
    title = state.get("title", "transformation")

    logger.info(f"Processing chunk {idx + 1}/{total} for '{title}'")
    # The section hint lives in the system prompt so it can't bleed into the
    # output of extraction-style transformations that echo the user content.
    chunk_system_prompt = (
        f"{state['system_prompt']}\n\n"
        f"[Note: The input is section {idx + 1} of {total} of a larger "
        f"document. Apply the instructions to this section only.]"
    )
    payload = [
        SystemMessage(content=chunk_system_prompt),
        HumanMessage(content=state["chunk"]),
    ]
    async with _get_chunk_semaphore():
        chain = await provision_langchain_model(
            str(payload),
            state.get("model_id"),
            "transformation",
            max_tokens=state["output_buffer"],
        )
        response = await chain.ainvoke(payload)

    logger.info(f"Chunk {idx + 1}/{total} for '{title}' completed")
    return {"chunk_results": [{"idx": idx, "result": _extract_response_content(response)}]}


def _batch_results_by_tokens(results: List[str], budget: int) -> List[List[str]]:
    """Greedily group consecutive results so each group fits within ``budget``
    tokens. A lone result that exceeds the budget gets its own group."""
    batches: List[List[str]] = []
    current: List[str] = []
    current_tokens = 0
    for r in results:
        t = token_count(r)
        if current and current_tokens + t > budget:
            batches.append(current)
            current, current_tokens = [], 0
        current.append(r)
        current_tokens += t
    if current:
        batches.append(current)
    return batches


async def _synthesize_once(
    results: List[str], state: dict, synthesis_prompt: str
) -> str:
    """One synthesis LLM call merging a list of partial results."""
    combined_text = "\n\n---\n\n".join(
        f"## Result from Part {i + 1}:\n{r}" for i, r in enumerate(results)
    )
    payload = [
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content=combined_text),
    ]
    async with _get_chunk_semaphore():
        chain = await provision_langchain_model(
            str(payload),
            state.get("model_id"),
            "transformation",
            max_tokens=state.get("output_buffer", DEFAULT_OUTPUT_TOKENS),
        )
        response = await chain.ainvoke(payload)
    return _extract_response_content(response)


async def _reduce_results(
    results: List[str], state: dict, synthesis_prompt: str, budget: int
) -> str:
    """Hierarchically reduce many chunk results into one, in rounds, so the
    combined synthesis input never exceeds the model's context window."""
    round_num = 0
    while len(results) > 1:
        round_num += 1
        batches = _batch_results_by_tokens(results, budget)
        # If nothing grouped (each result alone exceeds budget), force pairs so
        # the reduction always makes progress.
        if len(batches) == len(results):
            batches = [results[i : i + 2] for i in range(0, len(results), 2)]
        logger.info(
            f"Synthesis reduce round {round_num}: {len(results)} results -> "
            f"{len(batches)} batch(es)"
        )
        next_results: List[str] = []
        for batch in batches:
            if len(batch) == 1:
                next_results.append(batch[0])
            else:
                next_results.append(
                    await _synthesize_once(batch, state, synthesis_prompt)
                )
        results = next_results
    return results[0]


async def synthesize_results(state: dict, config: RunnableConfig) -> dict:
    """Synthesize chunk results into the final output (no-op if full content
    already succeeded)."""
    source = _get_source(state)
    title = state.get("title") or state["transformation"].title

    if state.get("output") and not state.get("needs_chunking", False):
        return {}

    chunk_results: List[ChunkResult] = state.get("chunk_results", [])
    if not chunk_results:
        logger.warning(f"No chunk results to synthesize for '{title}'")
        return {"output": ""}

    sorted_results = sorted(chunk_results, key=lambda x: x["idx"])

    if len(sorted_results) == 1:
        result = sorted_results[0]["result"]
        if source:
            await source.add_insight(title, result)
        return {"output": result}

    logger.info(f"Synthesizing {len(sorted_results)} chunk results for '{title}'")
    synthesis_prompt = f"""You previously processed a large document in {len(sorted_results)} parts using the following instructions:

{state.get("system_prompt", "")}

Below are the results from each part. Your task is to synthesize these into a single, coherent output that combines the key information from all parts. Remove any redundancy and create a unified result.

Do NOT simply concatenate - intelligently merge and synthesize the information."""

    # Budget the synthesis input to the context window so combining many results
    # (or large results) never overflows.
    context_limit = state.get("context_limit") or DEFAULT_CONTEXT_LIMIT
    output_buffer = state.get("output_buffer", DEFAULT_OUTPUT_TOKENS)
    budget = max(
        int(context_limit * SAFETY_BUFFER)
        - token_count(synthesis_prompt)
        - output_buffer,
        1000,
    )

    result = await _reduce_results(
        [r["result"] for r in sorted_results], state, synthesis_prompt, budget
    )

    logger.info(f"Completed transformation '{title}' with parallel chunking")
    if source:
        await source.add_insight(title, result)
    return {"output": result}


# Build the graph
agent_state = StateGraph(TransformationState)
agent_state.add_node("try_full", try_full_content)  # type: ignore[type-var]
agent_state.add_node("process_chunk", process_chunk)  # type: ignore[type-var]
agent_state.add_node("synthesize", synthesize_results)  # type: ignore[type-var]
agent_state.add_edge(START, "try_full")
agent_state.add_conditional_edges("try_full", fan_out_chunks, ["process_chunk", "synthesize"])
agent_state.add_edge("process_chunk", "synthesize")
agent_state.add_edge("synthesize", END)
graph = agent_state.compile()
