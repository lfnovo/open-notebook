import asyncio
import traceback
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from api.routers._chat_shared import (
    ChatMessage,
    SuccessResponse,
    extract_chat_messages,
    get_session_or_404,
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
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.exceptions import (
    IncompleteGenerationError,
    NotFoundError,
    OpenNotebookError,
)
from open_notebook.graphs.chat import NODE_NAME as CHAT_NODE
from open_notebook.graphs.chat import build_chat_payload
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.utils import clean_thinking_content, token_count
from open_notebook.utils.context_builder import build_notebook_context
from open_notebook.utils.graph_utils import (
    discard_message,
    get_session_message_count,
    invoke_chat_turn,
    persist_pending_human_turn,
    persist_state,
)

router = APIRouter()


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


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(notebook_id: str = Query(..., description="Notebook ID")):
    """Get all chat sessions for a notebook."""
    try:
        # Get notebook to verify it exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Get sessions for this notebook
        sessions_list = await notebook.get_chat_sessions()

        results = []
        for session in sessions_list:
            session_id = str(session.id)

            # Get message count from LangGraph state
            msg_count = await get_session_message_count(chat_graph, session_id)

            results.append(
                ChatSessionResponse(
                    id=session.id or "",
                    title=session.title or "Untitled Session",
                    notebook_id=notebook_id,
                    created=str(session.created),
                    updated=str(session.updated),
                    message_count=msg_count,
                    model_override=getattr(session, "model_override", None),
                )
            )

        return results
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat sessions: {str(e)}"
        )


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Create new session
        session = ChatSession(
            title=request.title
            or f"Chat Session {asyncio.get_event_loop().time():.0f}",
            model_override=request.model_override,
        )
        await session.save()

        # Relate session to notebook
        await session.relate_to_notebook(request.notebook_id)

        return ChatSessionResponse(
            id=session.id or "",
            title=session.title or "",
            notebook_id=request.notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=0,
            model_override=session.model_override,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating chat session: {str(e)}"
        )


@router.get(
    "/chat/sessions/{session_id}", response_model=ChatSessionWithMessagesResponse
)
async def get_session(session_id: str):
    """Get a specific session with its messages."""
    try:
        # Get session (normalizes the ID and 404s if missing)
        full_session_id, session = await get_session_or_404(session_id)

        # Get session state from LangGraph to retrieve messages
        # Use sync get_state() in a thread since SqliteSaver doesn't support async
        thread_state = await asyncio.to_thread(
            chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": full_session_id}),
        )

        # Extract messages from state
        messages: list[ChatMessage] = []
        if thread_state and thread_state.values and "messages" in thread_state.values:
            messages = extract_chat_messages(thread_state.values["messages"])

        # Find notebook_id (we need to query the relationship)
        notebook_query = await repo_query(
            "SELECT out FROM refers_to WHERE in = $session_id",
            {"session_id": ensure_record_id(full_session_id)},
        )

        notebook_id = notebook_query[0]["out"] if notebook_query else None

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
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """Update session title."""
    try:
        # Get session (normalizes the ID and 404s if missing)
        full_session_id, session = await get_session_or_404(session_id)

        update_data = request.model_dump(exclude_unset=True)

        if "title" in update_data:
            session.title = update_data["title"]

        if "model_override" in update_data:
            session.model_override = update_data["model_override"]

        await session.save()

        # Find notebook_id
        notebook_query = await repo_query(
            "SELECT out FROM refers_to WHERE in = $session_id",
            {"session_id": ensure_record_id(full_session_id)},
        )
        notebook_id = notebook_query[0]["out"] if notebook_query else None

        # Get message count from LangGraph state
        msg_count = await get_session_message_count(chat_graph, full_session_id)

        return ChatSessionResponse(
            id=session.id or "",
            title=session.title or "",
            notebook_id=notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=msg_count,
            model_override=session.model_override,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")


@router.delete("/chat/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: str):
    """Delete a chat session."""
    try:
        # Get session (normalizes the ID and 404s if missing)
        _full_session_id, session = await get_session_or_404(session_id)

        await session.delete()

        return SuccessResponse(success=True, message="Session deleted successfully")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@router.post("/chat/execute", response_model=ExecuteChatResponse)
async def execute_chat(request: ExecuteChatRequest):
    """Execute a chat request and get AI response."""
    try:
        # Verify session exists (normalizes the ID and 404s if missing)
        full_session_id, session = await get_session_or_404(request.session_id)

        # Fetch notebook linked to this session
        notebook_query = await repo_query(
            "SELECT out FROM refers_to WHERE in = $session_id",
            {"session_id": ensure_record_id(full_session_id)},
        )
        notebook = None
        if notebook_query:
            notebook = await Notebook.get(notebook_query[0]["out"])

        # Determine model override (per-request override takes precedence over session-level)
        model_override = (
            request.model_override
            if request.model_override is not None
            else getattr(session, "model_override", None)
        )

        # Get current state
        # Use sync get_state() in a thread since SqliteSaver doesn't support async
        current_state = await asyncio.to_thread(
            chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": full_session_id}),
        )

        # Prepare state for execution
        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["context"] = request.context
        state_values["notebook"] = notebook
        state_values["model_override"] = model_override

        # Add user message to state
        # Explicit id so a failed turn can remove it from the checkpoint.
        user_message = HumanMessage(content=request.message, id=str(uuid4()))
        state_values["messages"].append(user_message)

        # Execute chat graph in a thread so the synchronous LangGraph invoke
        # (SqliteSaver checkpoints are sync) doesn't block the event loop and
        # freeze the rest of the API while the LLM responds. Mirrors the
        # get_state() calls above.
        # invoke_chat_turn also drops the question from the checkpoint when the
        # turn fails, so a retry doesn't add it twice.
        result = await asyncio.to_thread(
            invoke_chat_turn,
            chat_graph,
            state_values,
            RunnableConfig(
                configurable={
                    "thread_id": full_session_id,
                    "model_id": model_override,
                }
            ),
            user_message,
        )

        # Update session timestamp
        await session.save()

        # Convert messages to response format
        messages = extract_chat_messages(result.get("messages", []))

        return ExecuteChatResponse(session_id=request.session_id, messages=messages)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        # Log detailed error with context for debugging
        logger.error(
            f"Error executing chat: {str(e)}\n"
            f"  Session ID: {request.session_id}\n"
            f"  Model override: {request.model_override}\n"
            f"  Traceback:\n{traceback.format_exc()}"
        )
        raise HTTPException(status_code=500, detail=f"Error executing chat: {str(e)}")


async def _settle_turn(thread_id: str, content: str, question: HumanMessage) -> None:
    """Persist what a streamed turn produced, or drop the question if nothing.

    Called on every exit path that did not already persist the answer: a partial
    answer is kept (with the question), a turn that produced nothing is rolled
    back so a retry doesn't stack the same question twice.
    """
    if content.strip():
        await persist_state(
            chat_graph,
            thread_id,
            {"messages": [AIMessage(content=content)]},
            as_node=CHAT_NODE,
        )
    else:
        await discard_message(chat_graph, thread_id, question)


async def _settle_safely(
    thread_id: str, content: str, question: Optional[HumanMessage]
) -> None:
    """`_settle_turn` for teardown paths, where raising would mask the cause."""
    if not question:
        return
    try:
        await _settle_turn(thread_id, content, question)
    except Exception:
        logger.exception(f"Could not settle streamed turn in {thread_id}")


async def _stream_execute_chat(
    request: ExecuteChatRequest,
    http_request: Request,
    thread_id: str,
    session: Any,
    notebook: Optional[Notebook],
    model_override: Optional[str],
) -> AsyncGenerator[str, None]:
    """Stream one notebook-chat turn as SSE: `user_message` -> `token`… -> `complete`.

    Generation runs outside the graph (the model is streamed directly): the
    sync-node/SqliteSaver graph cannot yield tokens, and `astream` is the only
    way for a client disconnect to cancel the provider request instead of
    letting it run to completion. The turn is still checkpointed exactly like
    the buffered endpoint — question up front, answer (or partial answer) on the
    way out — so history is identical whichever endpoint ran it.
    """
    queue: "asyncio.Queue[Any]" = asyncio.Queue()
    outcome = StreamOutcome()
    parts: list[str] = []
    task: Optional["asyncio.Task[Any]"] = None
    question: Optional[HumanMessage] = None
    persisted = False
    settled = False

    try:
        # Snapshot the thread; the sync-node graph and its SqliteSaver
        # checkpointer have no async API, so reads go through a thread.
        current_state = await asyncio.to_thread(
            chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": thread_id}),
        )

        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["context"] = request.context
        state_values["notebook"] = notebook
        state_values["model_override"] = model_override

        # Explicit id so a failed turn can remove it from the checkpoint.
        question = HumanMessage(content=request.message, id=str(uuid4()))
        state_values["messages"].append(question)

        yield sse({"type": "user_message", "content": request.message})

        # Persist the question before generating: SSE returns tokens long before
        # the graph would checkpoint its input, and a disconnect must not lose
        # what the user asked.
        await persist_pending_human_turn(
            chat_graph, thread_id, question, as_node=CHAT_NODE
        )
        persisted = True

        # Same prompt the node builds, so streamed and buffered answers match.
        payload = await asyncio.to_thread(build_chat_payload, state_values)  # type: ignore[arg-type]

        model = await provision_langchain_model(
            str(payload),
            model_override,
            "chat",
            max_tokens=8192,
            streaming=True,
        )

        task = asyncio.create_task(run_generation(queue, model, payload, parts))
        async for frame in stream_events(
            queue, outcome, is_disconnected=http_request.is_disconnected
        ):
            yield frame

        content = clean_thinking_content("".join(parts))

        if outcome.kind == "done":
            if not content.strip():
                # Raised here so the handler below settles (rolls back) the turn.
                raise IncompleteGenerationError(EMPTY_REPLY_MESSAGE)
            await persist_state(
                chat_graph,
                thread_id,
                {"messages": [AIMessage(content=content)]},
                as_node=CHAT_NODE,
            )
            settled = True
            await session.save()
            yield sse({"type": "complete", "content": content})
            return

        if outcome.kind == "timeout":
            await _settle_safely(thread_id, content, question)
            settled = True
            yield format_error_event(
                IncompleteGenerationError(
                    "The model did not finish within "
                    f"{int(MAX_STREAM_SECONDS)}s. Partial answer kept."
                )
            )
            return

        if outcome.kind == "error":
            await _settle_safely(thread_id, content, question)
            settled = True
            yield format_error_event(outcome.payload)
            return

        # Disconnected: keep whatever arrived; the client is gone.
        await _settle_safely(thread_id, content, question)
        settled = True

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(
            f"Error streaming chat: {str(e)}\n"
            f"  Session ID: {request.session_id}\n"
            f"  Model override: {request.model_override}\n"
            f"  Traceback:\n{traceback.format_exc()}"
        )
        if persisted and question and not settled:
            await _settle_safely(
                thread_id, clean_thinking_content("".join(parts)), question
            )
            settled = True
        yield format_error_event(e)
    finally:

        async def _settle_if_needed() -> None:
            if persisted and question and not settled:
                await _settle_safely(
                    thread_id, clean_thinking_content("".join(parts)), question
                )

        await finalize_stream(task, _settle_if_needed)


@router.post("/chat/execute/stream")
async def execute_chat_stream(request: ExecuteChatRequest, http_request: Request):
    """Execute a chat request and stream the response as SSE.

    Additive sibling of `/chat/execute`, which stays for API consumers: same
    body, same persistence, but `text/event-stream` frames.
    """
    try:
        full_session_id, session = await get_session_or_404(request.session_id)

        notebook_query = await repo_query(
            "SELECT out FROM refers_to WHERE in = $session_id",
            {"session_id": ensure_record_id(full_session_id)},
        )
        notebook = None
        if notebook_query:
            notebook = await Notebook.get(notebook_query[0]["out"])

        model_override = (
            request.model_override
            if request.model_override is not None
            else getattr(session, "model_override", None)
        )

        return StreamingResponse(
            _stream_execute_chat(
                request,
                http_request,
                full_session_id,
                session,
                notebook,
                model_override,
            ),
            media_type="text/event-stream",
            headers=stream_headers(),
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error starting chat stream: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error streaming chat: {str(e)}")


@router.post("/chat/context", response_model=BuildContextResponse)
async def build_context(request: BuildContextRequest):
    """Build context for a notebook based on context configuration."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        context_data, total_content = await build_notebook_context(
            notebook, request.context_config
        )

        char_count = len(total_content)
        estimated_tokens = token_count(total_content) if total_content else 0

        return BuildContextResponse(
            context=context_data, token_count=estimated_tokens, char_count=char_count
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error building context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error building context: {str(e)}")
