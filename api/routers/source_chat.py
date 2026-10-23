import asyncio
from typing import Any, AsyncGenerator, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from api.routers._chat_shared import (
    ChatMessage,
    SuccessResponse,
    extract_chat_messages,
    get_source_or_404,
    get_verified_source_session,
)
from api.routers._sse import (
    EMPTY_REPLY_MESSAGE,
    MAX_STREAM_SECONDS,
    StreamOutcome,
    finalize_stream,
    format_error_event,
    run_generation,
    sse,
    stream_events,
    stream_headers,
)
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession
from open_notebook.exceptions import (
    IncompleteGenerationError,
    NotFoundError,
    OpenNotebookError,
)
from open_notebook.graphs.source_chat import NODE_NAME as SOURCE_CHAT_NODE
from open_notebook.graphs.source_chat import prepare_source_chat_turn
from open_notebook.graphs.source_chat import source_chat_graph as source_chat_graph
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.graph_utils import (
    discard_message,
    get_session_message_count,
    persist_pending_human_turn,
    persist_state,
)

router = APIRouter()


# Request/Response models
class CreateSourceChatSessionRequest(BaseModel):
    source_id: str = Field(..., description="Source ID to create chat session for")
    title: Optional[str] = Field(None, description="Optional session title")
    model_override: Optional[str] = Field(
        None, description="Optional model override for this session"
    )


class UpdateSourceChatSessionRequest(BaseModel):
    title: Optional[str] = Field(None, description="New session title")
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )


class ContextIndicator(BaseModel):
    sources: List[str] = Field(
        default_factory=list, description="Source IDs used in context"
    )
    insights: List[str] = Field(
        default_factory=list, description="Insight IDs used in context"
    )
    notes: List[str] = Field(
        default_factory=list, description="Note IDs used in context"
    )


class SourceChatSessionResponse(BaseModel):
    id: str = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    source_id: str = Field(..., description="Source ID")
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")
    message_count: Optional[int] = Field(
        None, description="Number of messages in session"
    )


class SourceChatSessionWithMessagesResponse(SourceChatSessionResponse):
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Session messages"
    )
    context_indicators: Optional[ContextIndicator] = Field(
        None, description="Context indicators from last response"
    )


class SendMessageRequest(BaseModel):
    message: str = Field(..., description="User message content")
    model_override: Optional[str] = Field(
        None, description="Optional model override for this message"
    )


@router.post(
    "/sources/{source_id}/chat/sessions", response_model=SourceChatSessionResponse
)
async def create_source_chat_session(
    request: CreateSourceChatSessionRequest,
    source_id: str = Path(..., description="Source ID"),
):
    """Create a new chat session for a source."""
    try:
        # Verify source exists (normalizes the ID and 404s if missing)
        full_source_id, _source = await get_source_or_404(source_id)

        # Create new session with model_override support
        session = ChatSession(
            title=request.title or f"Source Chat {asyncio.get_event_loop().time():.0f}",
            model_override=request.model_override,
        )
        await session.save()

        # Relate session to source using "refers_to" relation
        await session.relate("refers_to", full_source_id)

        return SourceChatSessionResponse(
            id=session.id or "",
            title=session.title or "Untitled Session",
            source_id=source_id,
            model_override=session.model_override,
            created=str(session.created),
            updated=str(session.updated),
            message_count=0,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error creating source chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating source chat session: {str(e)}"
        )


@router.get(
    "/sources/{source_id}/chat/sessions", response_model=List[SourceChatSessionResponse]
)
async def get_source_chat_sessions(source_id: str = Path(..., description="Source ID")):
    """Get all chat sessions for a source."""
    try:
        # Verify source exists (normalizes the ID and 404s if missing)
        full_source_id, _source = await get_source_or_404(source_id)

        # Get sessions that refer to this source - first get relations, then sessions
        relations = await repo_query(
            "SELECT in FROM refers_to WHERE out = $source_id",
            {"source_id": ensure_record_id(full_source_id)},
        )

        sessions = []
        for relation in relations:
            session_id_raw = relation.get("in")
            if session_id_raw:
                session_id = str(session_id_raw)

                session_result = await repo_query(
                    "SELECT * FROM $id", {"id": ensure_record_id(session_id)}
                )
                if session_result and len(session_result) > 0:
                    session_data = session_result[0]

                    # Get message count from LangGraph state
                    msg_count = await get_session_message_count(
                        source_chat_graph, session_id
                    )

                    sessions.append(
                        SourceChatSessionResponse(
                            id=session_data.get("id") or "",
                            title=session_data.get("title") or "Untitled Session",
                            source_id=source_id,
                            model_override=session_data.get("model_override"),
                            created=str(session_data.get("created")),
                            updated=str(session_data.get("updated")),
                            message_count=msg_count,
                        )
                    )

        # Sort sessions by created date (newest first)
        sessions.sort(key=lambda x: x.created, reverse=True)
        return sessions
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching source chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching source chat sessions: {str(e)}"
        )


@router.get(
    "/sources/{source_id}/chat/sessions/{session_id}",
    response_model=SourceChatSessionWithMessagesResponse,
)
async def get_source_chat_session(
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Get a specific source chat session with its messages."""
    try:
        # Verify source + session exist and are related (404s otherwise)
        (
            _full_source_id,
            _source,
            full_session_id,
            session,
        ) = await get_verified_source_session(source_id, session_id)

        # Get session state from LangGraph to retrieve messages
        # Use sync get_state() in a thread since SqliteSaver doesn't support async
        thread_state = await asyncio.to_thread(
            source_chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": full_session_id}),
        )

        # Extract messages from state
        messages: list[ChatMessage] = []
        context_indicators = None

        if thread_state and thread_state.values:
            # Extract messages
            if "messages" in thread_state.values:
                messages = extract_chat_messages(thread_state.values["messages"])

            # Extract context indicators from the last state
            if "context_indicators" in thread_state.values:
                context_data = thread_state.values["context_indicators"]
                context_indicators = ContextIndicator(
                    sources=context_data.get("sources", []),
                    insights=context_data.get("insights", []),
                    notes=context_data.get("notes", []),
                )

        return SourceChatSessionWithMessagesResponse(
            id=session.id or "",
            title=session.title or "Untitled Session",
            source_id=source_id,
            model_override=getattr(session, "model_override", None),
            created=str(session.created),
            updated=str(session.updated),
            message_count=len(messages),
            messages=messages,
            context_indicators=context_indicators,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source or session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching source chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching source chat session: {str(e)}"
        )


@router.put(
    "/sources/{source_id}/chat/sessions/{session_id}",
    response_model=SourceChatSessionResponse,
)
async def update_source_chat_session(
    request: UpdateSourceChatSessionRequest,
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Update source chat session title and/or model override."""
    try:
        # Verify source + session exist and are related (404s otherwise)
        (
            _full_source_id,
            _source,
            full_session_id,
            session,
        ) = await get_verified_source_session(source_id, session_id)

        # Update session fields
        if request.title is not None:
            session.title = request.title
        if request.model_override is not None:
            session.model_override = request.model_override

        await session.save()

        # Get message count from LangGraph state
        msg_count = await get_session_message_count(source_chat_graph, full_session_id)

        return SourceChatSessionResponse(
            id=session.id or "",
            title=session.title or "Untitled Session",
            source_id=source_id,
            model_override=getattr(session, "model_override", None),
            created=str(session.created),
            updated=str(session.updated),
            message_count=msg_count,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source or session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error updating source chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating source chat session: {str(e)}"
        )


@router.delete(
    "/sources/{source_id}/chat/sessions/{session_id}", response_model=SuccessResponse
)
async def delete_source_chat_session(
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Delete a source chat session."""
    try:
        # Verify source + session exist and are related (404s otherwise)
        (
            _full_source_id,
            _source,
            full_session_id,
            session,
        ) = await get_verified_source_session(source_id, session_id)

        await session.delete()

        return SuccessResponse(
            success=True, message="Source chat session deleted successfully"
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source or session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting source chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting source chat session: {str(e)}"
        )


async def _settle_source_turn(
    thread_id: str, content: str, question: HumanMessage
) -> None:
    """Persist what a streamed turn produced, or drop the question if nothing."""
    if content.strip():
        await persist_state(
            source_chat_graph,
            thread_id,
            {"messages": [AIMessage(content=content)]},
            as_node=SOURCE_CHAT_NODE,
        )
    else:
        await discard_message(source_chat_graph, thread_id, question)


async def _settle_source_safely(
    thread_id: str, content: str, question: Optional[HumanMessage]
) -> None:
    if not question:
        return
    try:
        await _settle_source_turn(thread_id, content, question)
    except Exception:
        logger.exception(f"Could not settle streamed source turn in {thread_id}")


async def stream_source_chat_response(
    session_id: str,
    source_id: str,
    message: str,
    model_override: Optional[str] = None,
    *,
    http_request: Optional[Request] = None,
    session: Any = None,
) -> AsyncGenerator[str, None]:
    """Stream the source chat response as Server-Sent Events.

    Same contract as notebook chat: `user_message` -> `token`… ->
    (`context_indicators`) -> `complete`, with keepalives while the model is in
    prefill and cancellation of the provider request when the client goes away.
    """
    queue: "asyncio.Queue[Any]" = asyncio.Queue()
    outcome = StreamOutcome()
    parts: list[str] = []
    task: Optional["asyncio.Task[Any]"] = None
    question: Optional[HumanMessage] = None
    persisted = False
    settled = False

    try:
        # Snapshot the thread; SqliteSaver has no async API, so off the loop.
        current_state = await asyncio.to_thread(
            source_chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": session_id}),
        )

        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["source_id"] = source_id
        state_values["model_override"] = model_override

        # Explicit id so a failed turn can remove it from the checkpoint.
        question = HumanMessage(content=message, id=str(uuid4()))
        state_values["messages"].append(question)

        yield sse({"type": "user_message", "content": message, "timestamp": None})

        await persist_pending_human_turn(
            source_chat_graph, session_id, question, as_node=SOURCE_CHAT_NODE
        )
        persisted = True

        # Context building is I/O heavy (and sync) — keep it off the loop. It
        # also produces the state delta the node would have returned.
        turn = await asyncio.to_thread(prepare_source_chat_turn, state_values)  # type: ignore[arg-type]

        model = await provision_langchain_model(
            str(turn.payload),
            model_override,
            "chat",
            max_tokens=8192,
            streaming=True,
        )

        task = asyncio.create_task(run_generation(queue, model, turn.payload, parts))
        async for frame in stream_events(
            queue,
            outcome,
            is_disconnected=(
                http_request.is_disconnected if http_request is not None else None
            ),
        ):
            yield frame

        content = clean_thinking_content("".join(parts))

        if outcome.kind == "done":
            if not content.strip():
                raise IncompleteGenerationError(EMPTY_REPLY_MESSAGE)
            await persist_state(
                source_chat_graph,
                session_id,
                {"messages": [AIMessage(content=content)], **turn.updates},
                as_node=SOURCE_CHAT_NODE,
            )
            settled = True
            if session is not None:
                await session.save()
            if "context_indicators" in turn.updates:
                yield sse(
                    {
                        "type": "context_indicators",
                        "data": turn.updates["context_indicators"],
                    }
                )
            yield sse({"type": "complete", "content": content})
            return

        if outcome.kind == "timeout":
            await _settle_source_safely(session_id, content, question)
            settled = True
            yield format_error_event(
                IncompleteGenerationError(
                    "The model did not finish within "
                    f"{int(MAX_STREAM_SECONDS)}s. Partial answer kept."
                )
            )
            return

        if outcome.kind == "error":
            await _settle_source_safely(session_id, content, question)
            settled = True
            yield format_error_event(outcome.payload)
            return

        await _settle_source_safely(session_id, content, question)
        settled = True

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Error in source chat streaming: {str(e)}")
        if persisted and question and not settled:
            await _settle_source_safely(
                session_id, clean_thinking_content("".join(parts)), question
            )
            settled = True
        yield format_error_event(e)
    finally:

        async def _settle_if_needed() -> None:
            if persisted and question and not settled:
                await _settle_source_safely(
                    session_id, clean_thinking_content("".join(parts)), question
                )

        await finalize_stream(task, _settle_if_needed)


@router.post("/sources/{source_id}/chat/sessions/{session_id}/messages")
async def send_message_to_source_chat(
    request: SendMessageRequest,
    http_request: Request,
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Send a message to source chat session with SSE streaming response."""
    try:
        # Verify source + session exist and are related (404s otherwise)
        (
            full_source_id,
            _source,
            full_session_id,
            session,
        ) = await get_verified_source_session(source_id, session_id)

        if not request.message:
            raise HTTPException(status_code=400, detail="Message content is required")

        # Determine model override (request override takes precedence over session override)
        model_override = request.model_override or getattr(
            session, "model_override", None
        )

        # Update session timestamp
        await session.save()

        # Return streaming response
        return StreamingResponse(
            stream_source_chat_response(
                session_id=full_session_id,
                source_id=full_source_id,
                message=request.message,
                model_override=model_override,
                http_request=http_request,
                session=session,
            ),
            media_type="text/event-stream",
            headers=stream_headers(),
        )

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error sending message to source chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")
