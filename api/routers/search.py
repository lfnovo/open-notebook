import asyncio
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from api.models import (
    AskRequest,
    AskResponse,
    ResearchRequest,
    ResearchResponse,
    SearchRequest,
    SearchResponse,
)
from langchain_core.messages import HumanMessage
from open_notebook.domain.models import Model, model_manager
from open_notebook.domain.notebook import text_search, vector_search
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.graphs.ask import graph as ask_graph
from open_notebook.graphs.research import build_runnable_config, graph as research_graph

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(search_request: SearchRequest):
    """Search the knowledge base using text or vector search."""
    try:
        if search_request.type == "vector":
            # Check if embedding model is available for vector search
            if not await model_manager.get_embedding_model():
                raise HTTPException(
                    status_code=400,
                    detail="Vector search requires an embedding model. Please configure one in the Models section.",
                )

            results = await vector_search(
                keyword=search_request.query,
                results=search_request.limit,
                source=search_request.search_sources,
                note=search_request.search_notes,
                minimum_score=search_request.minimum_score,
            )
        else:
            # Text search
            results = await text_search(
                keyword=search_request.query,
                results=search_request.limit,
                source=search_request.search_sources,
                note=search_request.search_notes,
            )

        return SearchResponse(
            results=results or [],
            total_count=len(results) if results else 0,
            search_type=search_request.type,
        )

    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        logger.error(f"Database error during search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


async def stream_ask_response(
    question: str, strategy_model: Model, answer_model: Model, final_answer_model: Model
) -> AsyncGenerator[str, None]:
    """Stream the ask response as Server-Sent Events."""
    try:
        final_answer = None

        async for chunk in ask_graph.astream(
            input=dict(question=question),
            config=dict(
                configurable=dict(
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )
            ),
            stream_mode="updates",
        ):
            if "agent" in chunk:
                strategy_data = {
                    "type": "strategy",
                    "reasoning": chunk["agent"]["strategy"].reasoning,
                    "searches": [
                        {"term": search.term, "instructions": search.instructions}
                        for search in chunk["agent"]["strategy"].searches
                    ],
                }
                yield f"data: {strategy_data}\n\n"

            elif "provide_answer" in chunk:
                for answer in chunk["provide_answer"]["answers"]:
                    answer_data = {"type": "answer", "content": answer}
                    yield f"data: {answer_data}\n\n"

            elif "write_final_answer" in chunk:
                final_answer = chunk["write_final_answer"]["final_answer"]
                final_data = {"type": "final_answer", "content": final_answer}
                yield f"data: {final_data}\n\n"

        # Send completion signal
        yield f"data: {{'type': 'complete', 'final_answer': '{final_answer}'}}\n\n"

    except Exception as e:
        logger.error(f"Error in ask streaming: {str(e)}")
        error_data = {"type": "error", "message": str(e)}
        yield f"data: {error_data}\n\n"


@router.post("/search/ask")
async def ask_knowledge_base(ask_request: AskRequest):
    """Ask the knowledge base a question using AI models."""
    try:
        # Validate models exist
        strategy_model = await Model.get(ask_request.strategy_model)
        answer_model = await Model.get(ask_request.answer_model)
        final_answer_model = await Model.get(ask_request.final_answer_model)

        if not strategy_model:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy model {ask_request.strategy_model} not found",
            )
        if not answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Answer model {ask_request.answer_model} not found",
            )
        if not final_answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Final answer model {ask_request.final_answer_model} not found",
            )

        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="Ask feature requires an embedding model. Please configure one in the Models section.",
            )

        # For streaming response
        return StreamingResponse(
            await stream_ask_response(
                ask_request.question, strategy_model, answer_model, final_answer_model
            ),
            media_type="text/plain",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ask operation failed: {str(e)}")


@router.post("/search/research", response_model=ResearchResponse)
async def run_research_synthesis(research_request: ResearchRequest):
    """Run the deep research agent against notebook content."""

    if not research_request.question.strip():
        raise HTTPException(status_code=400, detail="Research question cannot be empty")

    try:
        config = build_runnable_config(
            research_request.notebook_id, research_request.config_overrides
        )

        def _coerce_to_string(value, strip: bool = True):
            if value is None:
                return None
            if isinstance(value, str):
                return value.strip() if strip else value
            if hasattr(value, "content"):
                return _coerce_to_string(value.content, strip=strip)
            if isinstance(value, (list, tuple, set)):
                parts = [
                    _coerce_to_string(item, strip=strip)
                    for item in value
                ]
                parts = [part for part in parts if part]
                joined = "\n".join(parts)
                return joined.strip() if strip else joined
            text = str(value)
            return text.strip() if strip else text

        result = await research_graph.ainvoke(
            input={"messages": [HumanMessage(content=research_request.question.strip())]},
            config=config,
        )

        if not result:
            logger.error(
                "Deep research agent returned no result for question '{}'",
                research_request.question,
            )
            raise HTTPException(
                status_code=500,
                detail="Deep research agent returned an empty result. Check server logs for more details.",
            )

        if not isinstance(result, dict):
            logger.error(
                "Deep research agent returned an unexpected payload type {} for question '{}'",
                type(result),
                research_request.question,
            )
            raise HTTPException(
                status_code=500,
                detail="Deep research agent returned an unexpected response. Check server logs for more details.",
            )

        final_report_value = result.get("final_report")
        final_report = _coerce_to_string(final_report_value, strip=False)
        final_report_text = _coerce_to_string(final_report_value)

        if final_report_text and final_report_text.lower().startswith("error"):
            logger.error(
                "Deep research agent returned an error final report for question '{}': {}",
                research_request.question,
                final_report_text,
            )
            raise HTTPException(status_code=500, detail=final_report_text)

        if not final_report or not final_report.strip():
            reason_candidates = []

            def _collect_reason(raw_value):
                text = _coerce_to_string(raw_value)
                if text and text not in reason_candidates:
                    reason_candidates.append(text)

            _collect_reason(final_report_value)

            for key in ("error", "errors", "detail", "message", "debug"):
                _collect_reason(result.get(key))

            messages = result.get("messages")
            if isinstance(messages, (list, tuple)):
                preview = [_coerce_to_string(item) for item in messages[:3]]
                preview = [item for item in preview if item]
                if preview:
                    _collect_reason("; ".join(preview))
            else:
                _collect_reason(messages)

            reason_summary = " | ".join(reason_candidates[:3]) if reason_candidates else None
            if reason_summary and len(reason_summary) > 800:
                reason_summary = reason_summary[:797] + "..."

            logger.error(
                "Deep research agent failed to produce a final report for question '{}'. Result keys: {}. Extracted reasons: {}",
                research_request.question,
                list(result.keys()),
                reason_candidates or None,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Deep research agent failed to produce a final report: {reason_summary}"
                    if reason_summary
                    else "Deep research agent failed to produce a final report. Check server logs for more details."
                ),
            )

        notes = result.get("notes") or result.get("raw_notes") or []
        if isinstance(notes, str):
            notes = [notes]

        return ResearchResponse(
            final_report=final_report or "",
            notes=[str(item) for item in notes],
            research_brief=result.get("research_brief"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running research synthesis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Research synthesis failed: {str(e)}")


@router.post("/search/ask/simple", response_model=AskResponse)
async def ask_knowledge_base_simple(ask_request: AskRequest):
    """Ask the knowledge base a question and return a simple response (non-streaming)."""
    try:
        # Validate models exist
        strategy_model = await Model.get(ask_request.strategy_model)
        answer_model = await Model.get(ask_request.answer_model)
        final_answer_model = await Model.get(ask_request.final_answer_model)

        if not strategy_model:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy model {ask_request.strategy_model} not found",
            )
        if not answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Answer model {ask_request.answer_model} not found",
            )
        if not final_answer_model:
            raise HTTPException(
                status_code=400,
                detail=f"Final answer model {ask_request.final_answer_model} not found",
            )

        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="Ask feature requires an embedding model. Please configure one in the Models section.",
            )

        # Run the ask graph and get final result
        final_answer = None
        async for chunk in ask_graph.astream(
            input=dict(question=ask_request.question),
            config=dict(
                configurable=dict(
                    strategy_model=strategy_model.id,
                    answer_model=answer_model.id,
                    final_answer_model=final_answer_model.id,
                )
            ),
            stream_mode="updates",
        ):
            if "write_final_answer" in chunk:
                final_answer = chunk["write_final_answer"]["final_answer"]

        if not final_answer:
            raise HTTPException(status_code=500, detail="No answer generated")

        return AskResponse(answer=final_answer, question=ask_request.question)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in ask simple endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ask operation failed: {str(e)}")
