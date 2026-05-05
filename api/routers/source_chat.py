import asyncio
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from loguru import logger
from pydantic import BaseModel, Field

from api.auth import current_user_from_request
from api.services.model_policy_service import ensure_model_selection_allowed
from api.services.team_context_service import resolve_team_context
from open_notebook.config import LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Source
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
)
from open_notebook.graphs.source_chat import source_chat_graph as source_chat_graph
from open_notebook.graphs.source_chat import source_chat_state
from open_notebook.utils.graph_utils import get_session_message_count

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

class ChatMessage(BaseModel):
    id: str = Field(..., description="Message ID")
    type: str = Field(..., description="Message type (human|ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


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
    enable_web_search: Optional[bool] = Field(
        False, description="Whether to enable web search for this message"
    )

class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


@router.post(
    "/sources/{source_id}/chat/sessions", response_model=SourceChatSessionResponse
)
async def create_source_chat_session(
    request: CreateSourceChatSessionRequest,
    http_request: Request,
    source_id: str = Path(..., description="Source ID"),
):
    """Create a new chat session for a source."""
    try:
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        actor = current_user_from_request(http_request)
        team_id = await resolve_team_context(
            actor=actor,
            resource_type="source",
            resource_id=full_source_id,
        )
        await ensure_model_selection_allowed(
            actor=actor,
            model_id=request.model_override,
            default_type="chat",
            team_id=team_id,
        )

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
    except InvalidInputError as e:
        raise HTTPException(status_code=403, detail=str(e))
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
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

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

                    # Get message count from LangGraph state (use checkpoint file
                    # so we read the same sqlite file the streaming endpoint writes to)
                    msg_count = await get_session_message_count(
                        source_chat_graph,
                        session_id,
                        checkpoint_file=LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE,
                        state_graph=source_chat_state,
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
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Get session
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify session is related to this source
        relation_query = await repo_query(
            "SELECT * FROM refers_to WHERE in = $session_id AND out = $source_id",
            {
                "session_id": ensure_record_id(full_session_id),
                "source_id": ensure_record_id(full_source_id),
            },
        )

        if not relation_query:
            raise HTTPException(
                status_code=404, detail="Session not found for this source"
            )

        # Get session state from LangGraph using SqliteSaver (NOT the module-level
        # MemorySaver graph) so we read from the same checkpoint file that the
        # streaming endpoint writes to.
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE) as saver:
            temp_graph = source_chat_state.compile(checkpointer=saver)
            thread_state = await asyncio.to_thread(
                temp_graph.get_state,
                config=RunnableConfig(configurable={"thread_id": full_session_id}),
            )

        # Extract messages from state
        messages: list[ChatMessage] = []
        context_indicators = None

        if thread_state and thread_state.values:
            # Extract messages
            if "messages" in thread_state.values:
                for msg in thread_state.values["messages"]:
                    msg_type = msg.type if hasattr(msg, "type") else "unknown"
                    if msg_type not in ["human", "ai"]:
                        continue
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    if not content and hasattr(msg, "tool_calls") and msg.tool_calls:
                        continue  # Skip AI messages that only contain tool calls
                    messages.append(
                        ChatMessage(
                            id=getattr(msg, "id", f"msg_{len(messages)}"),
                            type=msg_type,
                            content=content,
                            timestamp=None,  # LangChain messages don't have timestamps by default
                        )
                    )

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
    except InvalidInputError as e:
        raise HTTPException(status_code=403, detail=str(e))
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
    http_request: Request,
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Update source chat session title and/or model override."""
    try:
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Get session
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify session is related to this source
        relation_query = await repo_query(
            "SELECT * FROM refers_to WHERE in = $session_id AND out = $source_id",
            {
                "session_id": ensure_record_id(full_session_id),
                "source_id": ensure_record_id(full_source_id),
            },
        )

        if not relation_query:
            raise HTTPException(
                status_code=404, detail="Session not found for this source"
            )
        actor = current_user_from_request(http_request)
        team_id = await resolve_team_context(
            actor=actor,
            resource_type="source",
            resource_id=full_source_id,
        )
        if request.model_override is not None:
            await ensure_model_selection_allowed(
                actor=actor,
                model_id=request.model_override,
                default_type="chat",
                team_id=team_id,
            )

        # Update session fields
        if request.title is not None:
            session.title = request.title
        if request.model_override is not None:
            session.model_override = request.model_override

        await session.save()

        # Get message count from LangGraph state (use checkpoint file
        # so we read the same sqlite file the streaming endpoint writes to)
        msg_count = await get_session_message_count(
            source_chat_graph,
            full_session_id,
            checkpoint_file=LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE,
            state_graph=source_chat_state,
        )

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
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Get session
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify session is related to this source
        relation_query = await repo_query(
            "SELECT * FROM refers_to WHERE in = $session_id AND out = $source_id",
            {
                "session_id": ensure_record_id(full_session_id),
                "source_id": ensure_record_id(full_source_id),
            },
        )

        if not relation_query:
            raise HTTPException(
                status_code=404, detail="Session not found for this source"
            )

        await session.delete()

        return SuccessResponse(
            success=True, message="Source chat session deleted successfully"
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source or session not found")
    except Exception as e:
        logger.error(f"Error deleting source chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting source chat session: {str(e)}"
        )


async def stream_source_chat_response(
    session_id: str,
    source_id: str,
    message: str,
    model_override: Optional[str] = None,
    enable_web_search: bool = False,
    team_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream the source chat response as Server-Sent Events."""
    try:
        # Get current state from SqliteSaver (same file the streaming writes to)
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE) as saver:
            temp_graph = source_chat_state.compile(checkpointer=saver)
            current_state = await asyncio.to_thread(
                temp_graph.get_state,
                config=RunnableConfig(configurable={"thread_id": session_id}),
            )

        # Prepare state for execution
        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["source_id"] = source_id
        state_values["model_override"] = model_override
        state_values["enable_web_search"] = enable_web_search

        # Add user message to state
        user_message = HumanMessage(content=message)
        state_values["messages"].append(user_message)

        # Send user message event
        user_event = {"type": "user_message", "content": message, "timestamp": None}
        yield f"data: {json.dumps(user_event)}\n\n"

        # Instead of invoke, use astream to yield chunks as they arrive from LangGraph
        config = RunnableConfig(
            configurable={
                "thread_id": session_id,
                "model_id": model_override,
                "team_id": team_id,
            }
        )
        
        # Stream the complete AI response if chunks weren't captured properly
        # (Fall back on final message if no chunks were streamed)
        yielded_ai_chunks = False
            
        async with AsyncSqliteSaver.from_conn_string(LANGGRAPH_SOURCE_CHAT_CHECKPOINT_FILE) as saver:
            async_graph = source_chat_state.compile(checkpointer=saver)
            
            # Use specific events based on LangChain's structure
            # V2 streaming sends specific events for chat models
            async for event in async_graph.astream_events(
                input=state_values, config=config, version="v2"
            ):
                kind = event["event"]
                
                # Debug output to terminal so we can see what's happening
                print(f"EVENT: {kind}")
                
                # We can also check chat_model_stream for base chat models
                if kind == "on_chat_model_stream" or kind == "on_llm_stream":
                    # We got a new chunk from the LLM
                    # V2 astream_events structure
                    if "chunk" in event["data"]:
                        chunk = event["data"]["chunk"]
                        
                        # Sometimes content is empty but we should still check it
                        if hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            yielded_ai_chunks = True
                            # If this is our first chunk but it's string content
                            if isinstance(content, str):
                                ai_event = {
                                    "type": "ai_message",
                                    "content": content,
                                    "timestamp": None,
                                }
                                yield f"data: {json.dumps(ai_event)}\n\n"
                                # A small sleep to yield control loop back to the server so it flushes
                                await asyncio.sleep(0.001)
                            # Also handle dict chunk types
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and "text" in c:
                                        if not c["text"].startswith("<web_search_results>") and not c["text"].endswith("</web_search_results>"):
                                            ai_event = {
                                                "type": "ai_message",
                                                "content": c["text"],
                                                "timestamp": None,
                                            }
                                            yield f"data: {json.dumps(ai_event)}\n\n"
                                            await asyncio.sleep(0.001)
                                    elif isinstance(c, str):
                                        if not c.startswith("<web_search_results>") and not c.endswith("</web_search_results>"):
                                            ai_event = {
                                                "type": "ai_message",
                                                "content": c,
                                                "timestamp": None,
                                            }
                                            yield f"data: {json.dumps(ai_event)}\n\n"
                                            await asyncio.sleep(0.001)
                                        
                        # Also handle direct content streams if chunk is just a string or dict
                        elif isinstance(chunk, str) and chunk:
                            if not chunk.startswith("<web_search_results>") and not chunk.endswith("</web_search_results>"):
                                yielded_ai_chunks = True
                                ai_event = {
                                    "type": "ai_message",
                                    "content": chunk,
                                    "timestamp": None,
                                }
                                yield f"data: {json.dumps(ai_event)}\n\n"
                                await asyncio.sleep(0.001)
                        elif isinstance(chunk, dict) and "content" in chunk and chunk["content"]:
                            if not chunk["content"].startswith("<web_search_results>") and not chunk["content"].endswith("</web_search_results>"):
                                yielded_ai_chunks = True
                                ai_event = {
                                    "type": "ai_message",
                                    "content": chunk["content"],
                                    "timestamp": None,
                                }
                                yield f"data: {json.dumps(ai_event)}\n\n"
                                await asyncio.sleep(0.001)
                            
                # Some models yield raw strings in astream_events instead of chunk objects
                elif kind == "on_chat_model_end":
                    if "output" in event["data"] and "content" in event["data"]["output"]:
                        # Capture the full message at the end just in case stream events were empty
                        if not yielded_ai_chunks:
                            yielded_ai_chunks = True
                            content = event["data"]["output"]["content"]
                            if isinstance(content, str):
                                if not content.startswith("<web_search_results>") and not content.endswith("</web_search_results>"):
                                    # Split into smaller chunks so it looks like streaming
                                    chunk_size = 50
                                    for i in range(0, len(content), chunk_size):
                                        ai_event = {
                                            "type": "ai_message",
                                            "content": content[i:i+chunk_size],
                                            "timestamp": None,
                                        }
                                        yield f"data: {json.dumps(ai_event)}\n\n"
                                        await asyncio.sleep(0.01)
                                    
                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    # Graph finished, we can extract any context_indicators from final state
                    final_state = event["data"]["output"]
                    
                    # Check for context indicators in the final state values
                    # With astream_events, output might look different depending on graph structure
                    if isinstance(final_state, dict):
                        context_indicators = None
                        if "source_chat_agent" in final_state and isinstance(final_state["source_chat_agent"], dict):
                            # Extract final message if not streamed
                            if not yielded_ai_chunks and "messages" in final_state["source_chat_agent"]:
                                msg = final_state["source_chat_agent"]["messages"]
                                if hasattr(msg, "content"):
                                    # Need to stream out chunk by chunk if we are falling back to the whole message
                                    # to ensure it at least shows up
                                    content_text = msg.content
                                    if content_text:
                                        # Split into smaller chunks so it looks like streaming
                                        chunk_size = 50
                                        for i in range(0, len(content_text), chunk_size):
                                            ai_event = {
                                                "type": "ai_message",
                                                "content": content_text[i:i+chunk_size],
                                                "timestamp": None,
                                            }
                                            yield f"data: {json.dumps(ai_event)}\n\n"
                                            await asyncio.sleep(0.01)
                                    
                            context_indicators = final_state["source_chat_agent"].get("context_indicators")
                        elif "context_indicators" in final_state:
                            context_indicators = final_state["context_indicators"]
                            
                        if context_indicators:
                            context_event = {
                                "type": "context_indicators",
                                "data": context_indicators,
                            }
                            yield f"data: {json.dumps(context_event)}\n\n"

        # Send completion signal
        completion_event = {"type": "complete"}
        yield f"data: {json.dumps(completion_event)}\n\n"

    except Exception as e:
        import traceback

        from open_notebook.utils.error_classifier import classify_error

        _, user_message = classify_error(e)
        logger.error(f"Error in source chat streaming: {str(e)}\n{traceback.format_exc()}")
        error_event = {"type": "error", "message": user_message}
        yield f"data: {json.dumps(error_event)}\n\n"


@router.post("/sources/{source_id}/chat/sessions/{session_id}/messages")
async def send_message_to_source_chat(
    request: SendMessageRequest,
    http_request: Request,
    source_id: str = Path(..., description="Source ID"),
    session_id: str = Path(..., description="Session ID"),
):
    """Send a message to source chat session with SSE streaming response."""
    try:
        # Verify source exists
        full_source_id = (
            source_id if source_id.startswith("source:") else f"source:{source_id}"
        )
        source = await Source.get(full_source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Verify session exists and is related to source
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify session is related to this source
        relation_query = await repo_query(
            "SELECT * FROM refers_to WHERE in = $session_id AND out = $source_id",
            {
                "session_id": ensure_record_id(full_session_id),
                "source_id": ensure_record_id(full_source_id),
            },
        )

        if not relation_query:
            raise HTTPException(
                status_code=404, detail="Session not found for this source"
            )

        if not request.message:
            raise HTTPException(status_code=400, detail="Message content is required")

        # Determine model override (request override takes precedence over session override)
        model_override = request.model_override or getattr(
            session, "model_override", None
        )
        actor = current_user_from_request(http_request)
        team_id = await resolve_team_context(
            actor=actor,
            resource_type="source",
            resource_id=full_source_id,
        )
        await ensure_model_selection_allowed(
            actor=actor,
            model_id=model_override,
            default_type="chat",
            team_id=team_id,
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
                enable_web_search=request.enable_web_search or False,
                team_id=team_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Tells Nginx/proxies not to buffer
            },
        )

    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message to source chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")
