"""
Transformation graph — applies LLM-driven transformations to source content.

For small documents the entire content is processed in one LLM call (same as
the original single-node graph). For large documents that exceed the model's
context window, the graph transparently splits the content into token-bounded
chunks, processes them in parallel via LangGraph Send, and hierarchically
synthesizes the results — all without any user configuration.
"""

import asyncio
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
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content
from open_notebook.utils.token_utils import (
    DEFAULT_CONTEXT_LIMIT,
    SAFETY_BUFFER,
    chunk_text_by_tokens,
    parse_context_limit_error,
    token_count,
)

# ── Constants ──────────────────────────────────────────────────────────

# Token budget for the full-content attempt (matching the original graph).
FULL_CONTENT_MAX_TOKENS = 8192

# Max concurrent chunk LLM calls. Prevents rate-limit storms when a
# document is split into many chunks, especially across concurrent
# worker jobs.
MAX_CONCURRENT_CHUNKS = 10

# Module-level semaphore shared by all process_chunk invocations.
_chunk_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)

# ── State types ────────────────────────────────────────────────────────


class ChunkResult(TypedDict):
    """Result from processing a single chunk."""

    index: int
    output: str


class TransformationState(TypedDict):
    """Shared graph state for the entire transformation pipeline."""

    input_text: str
    source: Optional[Source]
    transformation: Transformation
    output: str
    # Chunking fields — populated only when the full-content path fails
    chunks: List[str]
    chunk_results: Annotated[List[ChunkResult], operator.add]
    total_chunks: int
    # Parsed model context window (set when chunking is triggered)
    context_limit: int
    # Output token budget derived from context_limit (set alongside it)
    output_budget: int


class ChunkState(TypedDict):
    """Per-chunk state dispatched via Send."""

    input_text: str
    source: Optional[Source]
    transformation: Transformation
    chunk_index: int
    chunk_text: str
    total_chunks: int
    # Output token budget for this model (derived from context_limit)
    output_budget: int


# ── Helpers ────────────────────────────────────────────────────────────


def _get_source(state) -> Optional[Source]:
    source = state.get("source")
    return source if isinstance(source, Source) else None


def _get_content(state) -> str:
    content = state.get("input_text")
    if content:
        return content
    source = _get_source(state)
    if source:
        return source.full_text or ""
    return ""


def _build_system_prompt(state, instructions: str, section_hint: str = "") -> str:
    """Render the system prompt, optionally with a section context hint."""
    prompt_data = {**state, "instructions": instructions}
    if section_hint:
        prompt_data["section_context"] = section_hint
    return Prompter(prompt_template="transformation/execute").render(data=prompt_data)


def _extract_response_content(response) -> str:
    """Extract and clean text from an LLM response."""
    content = extract_text_content(response.content)
    return clean_thinking_content(content)


async def _handle_llm_error(exc: Exception, content: str, system_prompt: str) -> dict:
    """
    Handle an LLM error: context-limit errors trigger chunking, all others
    are re-raised with appropriate classification.
    """
    error_str = str(exc)
    parsed = parse_context_limit_error(error_str)

    if not parsed:
        # Not a context-limit error — re-raise classified
        exc_class, message = classify_error(exc)
        raise exc_class(message) from exc

    context_limit, _tokens_sent = parsed
    logger.info(f"Content exceeds context window ({context_limit}). Chunking.")

    # Calculate a safe chunk size: leave room for system prompt + output
    system_prompt_tokens = token_count(system_prompt)
    output_budget = min(FULL_CONTENT_MAX_TOKENS, int(context_limit * 0.10))
    max_chunk_tokens = context_limit - system_prompt_tokens - output_budget
    max_chunk_tokens = int(max_chunk_tokens * SAFETY_BUFFER)
    max_chunk_tokens = max(max_chunk_tokens, 512)

    chunks = chunk_text_by_tokens(content, max_chunk_tokens)

    if len(chunks) == 1:
        # Single chunk means even the split content is still too large
        # for this model's context window — propagate original error
        exc_class, message = classify_error(exc)
        raise exc_class(message) from exc

    logger.info(f"Split content into {len(chunks)} chunks")
    return {
        "output": "",
        "chunks": chunks,
        "total_chunks": len(chunks),
        "context_limit": context_limit,
        "output_budget": output_budget,
    }


# ── Graph nodes ────────────────────────────────────────────────────────


async def try_full_content(state: TransformationState, config: RunnableConfig) -> dict:
    """
    Optimistically process the full content in one call.

    On success, sets ``output`` and returns empty chunks. On a context-limit
    error, chunks the content for parallel processing.
    """
    source = _get_source(state)
    content = _get_content(state)
    assert source or content, "No content to transform"

    transformation: Transformation = state["transformation"]
    instructions = transformation.prompt

    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        instructions = (
            f"{default_prompts.transformation_instructions}\n\n{instructions}"
        )

    system_prompt = _build_system_prompt(state, instructions)
    content_str = str(content) if content else ""
    payload = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=content_str),
    ]

    # ── Optimistic full-content attempt ──────────────────────────────
    try:
        chain = await provision_langchain_model(
            str(payload),
            config.get("configurable", {}).get("model_id"),
            "transformation",
            max_tokens=FULL_CONTENT_MAX_TOKENS,
        )
        response = await chain.ainvoke(payload)
        output = _extract_response_content(response)
    except Exception as e:
        # Check if this is a context-limit error we can recover from
        return await _handle_llm_error(e, content, system_prompt)
    # ── End of LLM call section ───────────────────────────────────────

    if source:
        await source.add_insight(transformation.title, output)

    return {"output": output, "chunks": []}


def fan_out_or_synthesize(
    state: TransformationState,
) -> Union[List[Send], str]:
    """
    Route to chunk processing or directly to synthesis.

    Returns ``List[Send]`` for parallel chunk processing when chunks are
    present, or the string ``"synthesize"`` to skip directly to output.
    """
    chunks = state.get("chunks")
    if chunks:
        total = state.get("total_chunks", len(chunks))
        output_budget = state.get(
            "output_budget", FULL_CONTENT_MAX_TOKENS
        )
        return [
            Send(
                "process_chunk",
                {
                    "input_text": state.get("input_text", ""),
                    "source": _get_source(state),
                    "transformation": state["transformation"],
                    "chunk_index": i,
                    "chunk_text": chunk_text,
                    "total_chunks": total,
                    "output_budget": output_budget,
                },
            )
            for i, chunk_text in enumerate(chunks)
        ]
    # No chunking needed — output is already set by try_full_content
    return "synthesize"


async def process_chunk(state: ChunkState, config: RunnableConfig) -> dict:
    """Process a single chunk and return its partial result."""
    try:
        chunk_text = state["chunk_text"]
        transformation: Transformation = state["transformation"]
        chunk_index = state["chunk_index"]
        total_chunks = state["total_chunks"]

        instructions = transformation.prompt

        default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
        if default_prompts.transformation_instructions:
            instructions = (
                f"{default_prompts.transformation_instructions}\n\n{instructions}"
            )

        # Provide a section hint so the LLM knows this is part of a larger doc
        section_hint = (
            f"This is section {chunk_index + 1} of {total_chunks} of the source "
            f"document. Process this section according to the instructions."
        )

        system_prompt = _build_system_prompt(state, instructions, section_hint=section_hint)
        content_str = str(chunk_text) if chunk_text else ""
        payload = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=content_str),
        ]

        chunk_output_budget = state.get(
            "output_budget", FULL_CONTENT_MAX_TOKENS
        )
        async with _chunk_semaphore:
            chain = await provision_langchain_model(
                str(payload),
                config.get("configurable", {}).get("model_id"),
                "transformation",
                max_tokens=chunk_output_budget,
            )
            response = await chain.ainvoke(payload)
        cleaned = _extract_response_content(response)

        logger.debug(f"Processed chunk {chunk_index + 1}/{total_chunks}")
        return {"chunk_results": [{"index": chunk_index, "output": cleaned}]}
    except Exception as e:
        logger.error(
            "Failed to process chunk {}: {}", chunk_index + 1, e
        )
        # Don't re-raise: one chunk failure should not abort
        # sibling work. Synthesis will include a placeholder.
        return {
            "chunk_results": [
                {
                    "index": chunk_index,
                    "output": (
                        f"[Error processing section {chunk_index + 1} "
                        f"of {total_chunks}]"
                    ),
                }
            ]
        }


async def synthesize_results(
    state: TransformationState, config: RunnableConfig
) -> dict:
    """
    Synthesize partial chunk results into a final output.

    Handles three cases:
    1. No chunking happened — pass through the output from try_full_content.
    2. Single chunk result — use it directly.
    3. Multiple results — hierarchically reduce via LLM merging rounds.
    """
    output = state.get("output")
    if output:
        # Direct path — no chunking occurred
        return {"output": output}

    chunk_results: List[ChunkResult] = state.get("chunk_results", [])
    transformation: Transformation = state["transformation"]

    if len(chunk_results) == 0:
        return {"output": ""}

    if len(chunk_results) == 1:
        try:
            result = chunk_results[0]["output"]
            source = _get_source(state)
            if source:
                await source.add_insight(transformation.title, result)
            return {"output": result}
        except Exception as e:
            exc_class, message = classify_error(e)
            raise exc_class(message) from e

    instructions = transformation.prompt

    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        instructions = (
            f"{default_prompts.transformation_instructions}\n\n{instructions}"
        )

    # Sort by index to maintain document order
    results = sorted(chunk_results, key=lambda r: r["index"])
    texts = [r["output"] for r in results]

    # Use the model's actual context window and output budget (parsed
    # from the error that triggered chunking), with safe defaults.
    context_limit = state.get("context_limit", DEFAULT_CONTEXT_LIMIT)
    output_budget = state.get(
        "output_budget", int(context_limit * 0.10)
    )

    while len(texts) > 1:
        # Group texts within token budget
        groups: List[List[str]] = []
        current_group: List[str] = []
        current_tokens = 0

        for text in texts:
            t = token_count(text)
            if (
                current_tokens + t > context_limit - output_budget - 500
                and current_group
            ):
                groups.append(current_group)
                current_group = []
                current_tokens = 0
            current_group.append(text)
            current_tokens += t

        if current_group:
            groups.append(current_group)

        # Merge each group via LLM
        merged: List[str] = []
        made_progress = False

        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
                continue

            made_progress = True

            try:
                chain = await provision_langchain_model(
                    f"Merge {len(group)} results",
                    config.get("configurable", {}).get("model_id"),
                    "transformation",
                    max_tokens=output_budget,
                )
                merge_content = "\n\n---\n\n".join(
                    f"Section {i + 1}:\n{text}" for i, text in enumerate(group)
                )
                merge_prompt = (
                    f"Below are {len(group)} partial results from processing "
                    f"different sections of a document. Merge them into a single "
                    f"coherent output following this instruction: "
                    f"{instructions}\n\n{merge_content}"
                )
                response = await chain.ainvoke(
                    [
                        SystemMessage(
                            content="You are merging partial transformation "
                            "results into a final output."
                        ),
                        HumanMessage(content=merge_prompt),
                    ]
                )
                merged.append(_extract_response_content(response))
            except Exception as e:
                exc_class, message = classify_error(e)
                raise exc_class(message) from e

        if not made_progress:
            # All groups are single-item — the loop would never shrink.
            # Fall back to merging the smallest adjacent pair (preserving
            # document order so downstream transformations remain coherent).
            logger.warning(
                "Synthesis stalled: all {} groups are single items within "
                "the token budget (limit={}). "
                "Forcing pairwise merge of the smallest adjacent pair.",
                len(groups),
                context_limit,
            )

            # Find the adjacent pair with the smallest combined size
            min_combined = float("inf")
            merge_idx = 0
            for i in range(len(texts) - 1):
                combined = token_count(texts[i]) + token_count(texts[i + 1])
                if combined < min_combined:
                    min_combined = combined
                    merge_idx = i

            # If even the smallest adjacent pair exceeds the context
            # window, re-chunk oversized results so pieces fit in
            # future merge rounds, instead of returning raw partials.
            overhead = token_count(instructions) + 300
            if min_combined + overhead > context_limit:
                re_chunk_budget = max(
                    512,
                    int((context_limit - overhead) * 0.4),
                )
                logger.warning(
                    "No adjacent pair fits the context window (limit={}, "
                    "smallest pair={} tkn). Re-chunking {} texts at "
                    "{} tokens each for further synthesis.",
                    context_limit,
                    min_combined,
                    len(texts),
                    re_chunk_budget,
                )
                re_chunked: List[str] = []
                for chunk_text in texts:
                    if token_count(chunk_text) > re_chunk_budget:
                        re_chunked.extend(
                            chunk_text_by_tokens(
                                chunk_text,
                                max_chunk_tokens=re_chunk_budget,
                                overlap_chars=0,
                            )
                        )
                    else:
                        re_chunked.append(chunk_text)
                texts = re_chunked
                # Continue the loop to merge the re-chunked pieces
                continue

            left = texts[merge_idx]
            right = texts[merge_idx + 1]
            force_content = (
                f"Part 1:\n{left}\n\n---\n\nPart 2:\n{right}"
            )
            merge_prompt = (
                f"Merge the following two partial results into one "
                f"coherent output following this instruction: "
                f"{instructions}\n\n{force_content}"
            )
            try:
                chain = await provision_langchain_model(
                    merge_prompt,
                    config.get("configurable", {}).get("model_id"),
                    "transformation",
                    max_tokens=output_budget,
                )
                response = await chain.ainvoke(
                    [
                        SystemMessage(
                            content="You are merging partial transformation "
                            "results into a final output."
                        ),
                        HumanMessage(content=merge_prompt),
                    ]
                )
                merged_result = _extract_response_content(response)
                # Replace the merged pair with the result, preserving order
                texts = (
                    texts[:merge_idx]
                    + [merged_result]
                    + texts[merge_idx + 2 :]
                )
            except Exception as e:
                exc_class, message = classify_error(e)
                raise exc_class(message) from e
            continue

        texts = merged

    final_output = texts[0] if texts else ""
    try:
        source = _get_source(state)
        if source:
            await source.add_insight(transformation.title, final_output)
    except Exception as e:
        exc_class, message = classify_error(e)
        raise exc_class(message) from e

    return {"output": final_output}


# ── Graph construction ─────────────────────────────────────────────────

agent_state = StateGraph(TransformationState)

agent_state.add_node("try_full", try_full_content)
agent_state.add_node("process_chunk", process_chunk)
agent_state.add_node("synthesize", synthesize_results)

agent_state.add_edge(START, "try_full")

# try_full routes to process_chunk (via Send) when chunking, or to
# synthesize directly when the full content succeeded.
agent_state.add_conditional_edges(
    "try_full",
    fan_out_or_synthesize,
    {
        "process_chunk": "process_chunk",
        "synthesize": "synthesize",
    },
)

agent_state.add_edge("process_chunk", "synthesize")
agent_state.add_edge("synthesize", END)

graph = agent_state.compile()
