import asyncio
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from api.auth import current_user_from_request
from api.models import ResourceCapabilities
from api.routers.notebooks import _check_notebook_access
from api.services.model_policy_service import ensure_model_selection_allowed
from api.services.team_context_service import resolve_team_context
from api.services.workspace_capabilities import resolve_resource_capabilities
from open_notebook.config import LANGGRAPH_CHAT_CHECKPOINT_FILE
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
)
from open_notebook.graphs.chat import agent_state
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.utils.graph_utils import get_session_message_count

router = APIRouter()


def _record_id(table: str, record_id: str) -> str:
    return record_id if record_id.startswith(f"{table}:") else f"{table}:{record_id}"


def _can_use_resource(actor, capabilities) -> bool:
    if not capabilities.can_read:
        return False
    return not (actor is not None and actor.role == "admin" and not capabilities.can_manage)


async def _chat_session_capabilities(
    *,
    session: ChatSession,
    actor,
    notebook: Notebook | None = None,
):
    owner_id = str(session.owner_id) if getattr(session, "owner_id", None) else None
    workspace_id = (
        str(session.workspace_id) if getattr(session, "workspace_id", None) else None
    )
    if notebook:
        owner_id = owner_id or (
            str(notebook.owner_id) if getattr(notebook, "owner_id", None) else None
        )
        workspace_id = workspace_id or (
            str(notebook.workspace_id)
            if getattr(notebook, "workspace_id", None)
            else None
        )
    return await resolve_resource_capabilities(
        actor=actor,
        resource_type="chat_session",
        owner_id=owner_id,
        workspace_id=workspace_id,
        visibility="private",
    )


async def _notebook_id_for_session(session_id: str) -> Optional[str]:
    notebook_query = await repo_query(
        "SELECT out FROM refers_to WHERE in = $session_id",
        {"session_id": ensure_record_id(session_id)},
    )
    return str(notebook_query[0]["out"]) if notebook_query else None


async def _ensure_session_notebook_owner(
    session_id: str,
    user_id: Optional[str],
    actor=None,
    session: Optional[ChatSession] = None,
) -> Optional[str]:
    notebook_id = await _notebook_id_for_session(session_id)
    if not notebook_id:
        if session is not None:
            capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
            )
            if not capabilities.can_delete:
                raise HTTPException(status_code=403, detail="Access denied")
        return None

    notebook = await Notebook.get(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if actor is not None:
        capabilities = await _chat_session_capabilities(
            session=session or ChatSession(owner_id=user_id),
            actor=actor,
            notebook=notebook,
        )
        if not capabilities.can_delete:
            raise HTTPException(status_code=403, detail="Access denied")
        return notebook_id

    if not _check_notebook_access(
        {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
        user_id,
        require_owner=True,
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return notebook_id


# Request/Response models
class CreateSessionRequest(BaseModel):
    notebook_id: str = Field(..., description="Notebook ID to create session for")
    title: Optional[str] = Field(None, description="Optional session title")
    model_override: Optional[str] = Field(
        None, description="Optional model override for this session"
    )


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, description="New session title")
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )


class ChatMessage(BaseModel):
    id: str = Field(..., description="Message ID")
    type: str = Field(..., description="Message type (human|ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatSessionResponse(BaseModel):
    id: str = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    notebook_id: Optional[str] = Field(None, description="Notebook ID")
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")
    message_count: Optional[int] = Field(
        None, description="Number of messages in session"
    )
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )
    capabilities: ResourceCapabilities = Field(default_factory=ResourceCapabilities)


class ChatSessionWithMessagesResponse(ChatSessionResponse):
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Session messages"
    )


class ExecuteChatRequest(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    message: str = Field(..., description="User message content")
    context: Dict[str, Any] = Field(
        ..., description="Chat context with sources and notes"
    )
    model_override: Optional[str] = Field(
        None, description="Optional model override for this message"
    )
    enable_web_search: Optional[bool] = Field(
        False, description="Whether to enable web search for this message"
    )


class ExecuteChatResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(..., description="Updated message list")


class BuildContextRequest(BaseModel):
    notebook_id: str = Field(..., description="Notebook ID")
    context_config: Dict[str, Any] = Field(..., description="Context configuration")


class BuildContextResponse(BaseModel):
    context: Dict[str, Any] = Field(..., description="Built context data")
    token_count: int = Field(..., description="Estimated token count")
    char_count: int = Field(..., description="Character count")


class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(
    request: Request,
    notebook_id: str = Query(..., description="Notebook ID"),
):
    """Get all chat sessions for a notebook."""
    try:
        # Get notebook to verify it exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        actor = current_user_from_request(request)
        notebook_capabilities = await resolve_resource_capabilities(
            actor=actor,
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
        if not notebook_capabilities.can_read:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get sessions for this notebook
        sessions_list = await notebook.get_chat_sessions()

        results = []
        for session in sessions_list:
            session_capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
                notebook=notebook,
            )
            if not session_capabilities.can_read:
                continue
            session_id = str(session.id)

            # Get message count from LangGraph state (use checkpoint file
            # so we read the same sqlite file the streaming endpoint writes to)
            msg_count = await get_session_message_count(
                chat_graph,
                session_id,
                checkpoint_file=LANGGRAPH_CHAT_CHECKPOINT_FILE,
                state_graph=agent_state,
            )

            results.append(
                ChatSessionResponse(
                    id=session.id or "",
                    title=session.title or "Untitled Session",
                    notebook_id=notebook_id,
                    created=str(session.created),
                    updated=str(session.updated),
                    message_count=msg_count,
                    model_override=getattr(session, "model_override", None),
                    capabilities=session_capabilities,
                )
            )

        return results
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat sessions: {str(e)}"
        )


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_session(request: CreateSessionRequest, http_request: Request):
    """Create a new chat session."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        actor = current_user_from_request(http_request)
        notebook_capabilities = await resolve_resource_capabilities(
            actor=actor,
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
        if not _can_use_resource(actor, notebook_capabilities):
            raise HTTPException(status_code=403, detail="Access denied")
        team_id = await resolve_team_context(
            actor=actor,
            resource_type="notebook",
            resource_id=request.notebook_id,
        )
        await ensure_model_selection_allowed(
            actor=actor,
            model_id=request.model_override,
            default_type="chat",
            team_id=team_id,
        )

        # Create new session
        session = ChatSession(
            title=request.title
            or f"Chat Session {asyncio.get_event_loop().time():.0f}",
            model_override=request.model_override,
            owner_id=actor.id if actor else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
        )
        await session.save()

        # Relate session to notebook
        await session.relate_to_notebook(request.notebook_id)
        session_capabilities = await _chat_session_capabilities(
            session=session,
            actor=actor,
            notebook=notebook,
        )

        return ChatSessionResponse(
            id=session.id or "",
            title=session.title or "",
            notebook_id=request.notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=0,
            model_override=session.model_override,
            capabilities=session_capabilities,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating chat session: {str(e)}"
        )


@router.get(
    "/chat/sessions/{session_id}", response_model=ChatSessionWithMessagesResponse
)
async def get_session(session_id: str, http_request: Request):
    """Get a specific session with its messages."""
    try:
        # Get session
        # Ensure session_id has proper table prefix
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        notebook_id = await _notebook_id_for_session(full_session_id)
        notebook = await Notebook.get(str(notebook_id)) if notebook_id else None
        actor = current_user_from_request(http_request)
        capabilities = await _chat_session_capabilities(
            session=session,
            actor=actor,
            notebook=notebook,
        )
        if not capabilities.can_read:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get session state from LangGraph using SqliteSaver (NOT the module-level
        # MemorySaver graph) so we read from the same checkpoint file that the
        # streaming endpoint writes to.
        from langgraph.checkpoint.sqlite import SqliteSaver

        from open_notebook.config import LANGGRAPH_CHAT_CHECKPOINT_FILE
        from open_notebook.graphs.chat import agent_state

        with SqliteSaver.from_conn_string(LANGGRAPH_CHAT_CHECKPOINT_FILE) as saver:
            temp_graph = agent_state.compile(checkpointer=saver)
            thread_state = await asyncio.to_thread(
                temp_graph.get_state,
                config=RunnableConfig(configurable={"thread_id": full_session_id}),
            )

        # Extract messages from state
        messages: list[ChatMessage] = []
        if thread_state and thread_state.values and "messages" in thread_state.values:
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

        if not notebook_id:
            # This might be an old session created before API migration
            logger.warning(
                f"No notebook relationship found for session {session_id} - may be an orphaned session"
            )

        return ChatSessionWithMessagesResponse(
            id=session.id or "",
            title=session.title or "Untitled Session",
            notebook_id=notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=len(messages),
            messages=messages,
            model_override=getattr(session, "model_override", None),
            capabilities=capabilities,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str, request: UpdateSessionRequest, http_request: Request
):
    """Update session title."""
    try:
        # Ensure session_id has proper table prefix
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        update_data = request.model_dump(exclude_unset=True)
        notebook_id = await _notebook_id_for_session(full_session_id)
        actor = current_user_from_request(http_request)
        team_id = None
        if notebook_id:
            notebook = await Notebook.get(notebook_id)
            capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
                notebook=notebook,
            )
            if not capabilities.can_update:
                raise HTTPException(status_code=403, detail="Access denied")
            team_id = await resolve_team_context(
                actor=actor,
                resource_type="notebook",
                resource_id=notebook_id,
            )
        else:
            capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
            )
            if not capabilities.can_update:
                raise HTTPException(status_code=403, detail="Access denied")
        if "model_override" in update_data:
            await ensure_model_selection_allowed(
                actor=actor,
                model_id=update_data["model_override"],
                default_type="chat",
                team_id=team_id,
            )

        if "title" in update_data:
            session.title = update_data["title"]

        if "model_override" in update_data:
            session.model_override = update_data["model_override"]

        await session.save()

        # Find notebook_id
        # Ensure session_id has proper table prefix
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        # Get message count from LangGraph state (use checkpoint file
        # so we read the same sqlite file the streaming endpoint writes to)
        msg_count = await get_session_message_count(
            chat_graph,
            full_session_id,
            checkpoint_file=LANGGRAPH_CHAT_CHECKPOINT_FILE,
            state_graph=agent_state,
        )

        return ChatSessionResponse(
            id=session.id or "",
            title=session.title or "",
            notebook_id=notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=msg_count,
            model_override=session.model_override,
            capabilities=capabilities,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")


@router.delete("/chat/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: str, http_request: Request):
    """Delete a chat session."""
    try:
        # Ensure session_id has proper table prefix
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        actor = current_user_from_request(http_request)
        await _ensure_session_notebook_owner(
            full_session_id,
            actor.id if actor else None,
            actor=actor,
            session=session,
        )

        await session.delete()

        return SuccessResponse(success=True, message="Session deleted successfully")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


async def stream_chat_response(
    session_id: str,
    message: str,
    context: dict,
    model_override: Optional[str] = None,
    enable_web_search: bool = False,
    team_id: Optional[str] = None,
):
    import json

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from open_notebook.config import LANGGRAPH_CHAT_CHECKPOINT_FILE
    from open_notebook.graphs.chat import agent_state
    
    try:
        # Get current state from SqliteSaver (same file the streaming writes to)
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(LANGGRAPH_CHAT_CHECKPOINT_FILE) as saver:
            temp_graph = agent_state.compile(checkpointer=saver)
            current_state = await asyncio.to_thread(
                temp_graph.get_state,
                config=RunnableConfig(configurable={"thread_id": session_id}),
            )

        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["context"] = context
        state_values["model_override"] = model_override
        state_values["enable_web_search"] = enable_web_search

        from langchain_core.messages import HumanMessage
        user_message = HumanMessage(content=message)
        state_values["messages"].append(user_message)

        user_event = {"type": "user_message", "content": message, "timestamp": None}
        yield f"data: {json.dumps(user_event)}\n\n"

        config = RunnableConfig(
            configurable={
                "thread_id": session_id,
                "model_id": model_override,
                "team_id": team_id,
            }
        )
        
        yielded_ai_chunks = False
            
        async with AsyncSqliteSaver.from_conn_string(LANGGRAPH_CHAT_CHECKPOINT_FILE) as saver:
            async_graph = agent_state.compile(checkpointer=saver)
            
            async for event in async_graph.astream_events(
                input=state_values, config=config, version="v2"
            ):
                kind = event["event"]
                
                if kind == "on_chat_model_stream" or kind == "on_llm_stream":
                    if "chunk" in event["data"]:
                        chunk = event["data"]["chunk"]
                        
                        if hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            yielded_ai_chunks = True
                            if isinstance(content, str):
                                if not content.startswith("<web_search_results>") and not content.endswith("</web_search_results>"):
                                    ai_event = {
                                        "type": "ai_message",
                                        "content": content,
                                        "timestamp": None,
                                    }
                                    yield f"data: {json.dumps(ai_event)}\n\n"
                                    await asyncio.sleep(0.001)
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
                            
                elif kind == "on_chat_model_end":
                    if "output" in event["data"] and "content" in event["data"]["output"]:
                        if not yielded_ai_chunks:
                            yielded_ai_chunks = True
                            content = event["data"]["output"]["content"]
                            if isinstance(content, str):
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
                    final_state = event["data"]["output"]
                    if isinstance(final_state, dict) and "agent" in final_state:
                        if not yielded_ai_chunks and "messages" in final_state["agent"]:
                            msg = final_state["agent"]["messages"]
                            if hasattr(msg, "content"):
                                content_text = msg.content
                                if content_text:
                                    chunk_size = 50
                                    for i in range(0, len(content_text), chunk_size):
                                        ai_event = {
                                            "type": "ai_message",
                                            "content": content_text[i:i+chunk_size],
                                            "timestamp": None,
                                        }
                                        yield f"data: {json.dumps(ai_event)}\n\n"
                                        await asyncio.sleep(0.01)

        completion_event = {"type": "complete"}
        yield f"data: {json.dumps(completion_event)}\n\n"

    except Exception as e:
        import traceback

        from open_notebook.utils.error_classifier import classify_error
        _, user_message = classify_error(e)
        logger.error(f"Error in chat streaming: {str(e)}\n{traceback.format_exc()}")
        error_event = {"type": "error", "message": user_message}
        yield f"data: {json.dumps(error_event)}\n\n"

from fastapi.responses import StreamingResponse


@router.post("/chat/execute")
async def execute_chat(request: ExecuteChatRequest, http_request: Request):
    """Execute a chat request and get AI response with SSE streaming."""
    try:
        # Verify session exists
        # Ensure session_id has proper table prefix
        full_session_id = (
            request.session_id
            if request.session_id.startswith("chat_session:")
            else f"chat_session:{request.session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Determine model override (per-request override takes precedence over session-level)
        model_override = (
            request.model_override
            if request.model_override is not None
            else getattr(session, "model_override", None)
        )
        notebook_id = await _notebook_id_for_session(full_session_id)
        actor = current_user_from_request(http_request)
        team_id = None
        if notebook_id:
            notebook = await Notebook.get(notebook_id)
            capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
                notebook=notebook,
            )
            if not _can_use_resource(actor, capabilities):
                raise HTTPException(status_code=403, detail="Access denied")
            team_id = await resolve_team_context(
                actor=actor,
                resource_type="notebook",
                resource_id=notebook_id,
            )
        else:
            capabilities = await _chat_session_capabilities(
                session=session,
                actor=actor,
            )
            if not _can_use_resource(actor, capabilities):
                raise HTTPException(status_code=403, detail="Access denied")
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
            stream_chat_response(
                session_id=full_session_id,
                message=request.message,
                context=request.context,
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
        logger.error(f"Error sending message to chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.post("/chat/context", response_model=BuildContextResponse)
async def build_context(request: BuildContextRequest, http_request: Request):
    """Build context for a notebook based on context configuration."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        actor = current_user_from_request(http_request)
        notebook_capabilities = await resolve_resource_capabilities(
            actor=actor,
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
        if not notebook_capabilities.can_read:
            raise HTTPException(status_code=403, detail="Access denied")

        context_data: dict[str, list[dict[str, str]]] = {"sources": [], "notes": []}
        total_content = ""
        notebook_sources = await notebook.get_sources()
        notebook_notes = await notebook.get_notes()
        sources_by_id = {
            str(source.id): source for source in notebook_sources if getattr(source, "id", None)
        }
        notes_by_id = {
            str(note.id): note for note in notebook_notes if getattr(note, "id", None)
        }

        # Process context configuration if provided
        if request.context_config:
            # Process sources
            for source_id, status in request.context_config.get("sources", {}).items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_source_id = _record_id("source", source_id)
                    source = sources_by_id.get(full_source_id)
                    if not source:
                        continue

                    if "insights" in status:
                        source_context = await source.get_context(context_size="short")
                        context_data["sources"].append(source_context)
                        total_content += str(source_context)
                    elif "full content" in status:
                        source_context = await source.get_context(context_size="long")
                        context_data["sources"].append(source_context)
                        total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source_id}: {str(e)}")
                    continue

            # Process notes
            for note_id, status in request.context_config.get("notes", {}).items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_note_id = _record_id("note", note_id)
                    note = notes_by_id.get(full_note_id)
                    if not note:
                        continue

                    if "full content" in status:
                        note_context = note.get_context(context_size="long")
                        context_data["notes"].append(note_context)
                        total_content += str(note_context)
                except Exception as e:
                    logger.warning(f"Error processing note {note_id}: {str(e)}")
                    continue
        else:
            # Default behavior - include all sources and notes with short context
            for source in notebook_sources:
                try:
                    source_context = await source.get_context(context_size="short")
                    context_data["sources"].append(source_context)
                    total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source.id}: {str(e)}")
                    continue

            for note in notebook_notes:
                try:
                    note_context = note.get_context(context_size="long")
                    context_data["notes"].append(note_context)
                    total_content += str(note_context)
                except Exception as e:
                    logger.warning(f"Error processing note {note.id}: {str(e)}")
                    continue

        # Calculate character and token counts
        char_count = len(total_content)
        # Use token count utility if available
        try:
            from open_notebook.utils import token_count

            estimated_tokens = token_count(total_content) if total_content else 0
        except ImportError:
            # Fallback to simple estimation
            estimated_tokens = char_count // 4

        return BuildContextResponse(
            context=context_data, token_count=estimated_tokens, char_count=char_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error building context: {str(e)}")
