import asyncio
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
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
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession
from open_notebook.exceptions import (
    NotFoundError,
    OpenNotebookError,
)
from open_notebook.graphs.source_chat import source_chat_graph as source_chat_graph
from open_notebook.utils.graph_utils import get_session_message_count

router = APIRouter()


# Seconds between SSE keepalive comments while the LLM generates. Keeps the
# connection from going idle so proxies (incl. the Next.js rewrite in front of
# FastAPI) don't drop it mid-generation.
KEEPALIVE_INTERVAL_SECONDS = 15.0


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
        _full_source_id, _source, full_session_id, session = (
            await get_verified_source_session(source_id, session_id)
        )

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
        _full_source_id, _source, full_session_id, session = (
            await get_verified_source_session(source_id, session_id)
        )

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
        _full_source_id, _source, full_session_id, session = (
            await get_verified_source_session(source_id, session_id)
        )

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


async def stream_source_chat_response(
    request: Request,
    session_id: str,
    source_id: str,
    message: str,
    model_override: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream the source chat response as Server-Sent Events."""
    config = RunnableConfig(
        configurable={"thread_id": session_id, "model_id": model_override}
    )
    invoke_task: Optional[asyncio.Task] = None
    try:
        # Persist the user message to the checkpoint up front so it survives a
        # mid-generation disconnect (the frontend refetches the checkpoint on
        # cancel/complete and would otherwise drop the user's message). Skip the
        # append when this exact message is already the trailing (unanswered)
        # turn — a retry after a failed generation would otherwise duplicate it.
        # A completed exchange always ends with an AI message, so a trailing
        # human turn is necessarily a pending one.
        current_state = await asyncio.to_thread(
            source_chat_graph.get_state, config=config
        )
        already_pending = False
        if current_state and current_state.values and "messages" in current_state.values:
            existing_messages = current_state.values["messages"]
            last_message = existing_messages[-1] if existing_messages else None
            already_pending = (
                isinstance(last_message, HumanMessage)
                and last_message.content == message
            )
        if not already_pending:
            await source_chat_graph.aupdate_state(
                config, {"messages": [HumanMessage(content=message)]}
            )

        # Send user message event
        user_event = {"type": "user_message", "content": message, "timestamp": None}
        yield f"data: {json.dumps(user_event)}\n\n"

        # Run the async graph with ainvoke so generation is cancellable. Only the
        # per-message config is passed as input; the messages (incl. the user
        # message above) are read from the checkpoint. The ignore is a langgraph
        # typing limitation: it accepts a partial state dict at runtime, but the
        # signature requires the full state type.
        invoke_task = asyncio.create_task(
            source_chat_graph.ainvoke(
                input={"source_id": source_id, "model_override": model_override},  # type: ignore[call-overload]
                config=config,
            )
        )
        while True:
            done, _ = await asyncio.wait(
                {invoke_task}, timeout=KEEPALIVE_INTERVAL_SECONDS
            )
            if done:
                # Re-raises on graph error, caught by the outer try/except below.
                result = invoke_task.result()
                break
            if await request.is_disconnected():
                # Client went away — stop generating instead of burning tokens.
                return
            # SSE comment — ignored by clients, keeps the connection alive.
            yield ": ping\n\n"

        # Stream the complete AI response
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "type") and msg.type == "ai":
                    ai_event = {
                        "type": "ai_message",
                        "content": msg.content if hasattr(msg, "content") else str(msg),
                        "timestamp": None,
                    }
                    yield f"data: {json.dumps(ai_event)}\n\n"

        # Stream context indicators
        if "context_indicators" in result:
            context_event = {
                "type": "context_indicators",
                "data": result["context_indicators"],
            }
            yield f"data: {json.dumps(context_event)}\n\n"

        # Send completion signal
        completion_event = {"type": "complete"}
        yield f"data: {json.dumps(completion_event)}\n\n"

    except Exception as e:
        from open_notebook.utils.error_classifier import classify_error

        _, error_message = classify_error(e)
        logger.error(f"Error in source chat streaming: {str(e)}")
        error_event = {"type": "error", "message": error_message}
        yield f"data: {json.dumps(error_event)}\n\n"
    finally:
        # Stop generation if the generator is torn down mid-flight (client
        # disconnect or server cancellation) so the model doesn't keep running.
        if invoke_task is not None and not invoke_task.done():
            invoke_task.cancel()
            await asyncio.gather(invoke_task, return_exceptions=True)


@router.post("/sources/{source_id}/chat/sessions/{session_id}/messages")
async def send_message_to_source_chat(
    http_request: Request,
    request: SendMessageRequest,
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Send a message to source chat session with SSE streaming response."""
    try:
        # Verify source + session exist and are related (404s otherwise)
        full_source_id, _source, full_session_id, session = (
            await get_verified_source_session(source_id, session_id)
        )

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
                http_request,
                session_id=full_session_id,
                source_id=full_source_id,
                message=request.message,
                model_override=model_override,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error sending message to source chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")
