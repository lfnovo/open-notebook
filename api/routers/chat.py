import asyncio
import traceback
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from api.routers import _sse
from api.routers._chat_shared import (
    ChatMessage,
    SuccessResponse,
    extract_chat_messages,
    get_session_or_404,
    release_session_lock,
    serialized_turn,
    session_lock,
)
from api.routers._sse import (
    EMPTY_REPLY_MESSAGE,
    StreamOutcome,
    ThinkingFilter,
    finalize_stream,
    format_error_event,
    run_graph,
    sse,
    sse_keepalive,
    stop_task,
    stream_events,
    stream_headers,
)
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Notebook
from open_notebook.exceptions import (
    ExternalServiceError,
    IncompleteGenerationError,
    NotFoundError,
    OpenNotebookError,
)
from open_notebook.graphs.chat import NODE_NAME as CHAT_NODE
from open_notebook.graphs.chat import graph as chat_graph
from open_notebook.utils import token_count
from open_notebook.utils.context_builder import build_notebook_context
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.graph_utils import (
    StreamEnd,
    ainvoke_chat_turn,
    get_session_message_count,
    last_ai_content,
    persist_pending_human_turn,
    settle_turn_end,
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
        ...,
        description=(
            "The `context` object returned by POST /api/chat/context "
            "(`sources` and `notes` lists with their content), not the "
            "`context_config` sent to that endpoint"
        ),
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
    context: Dict[str, Any] = Field(
        ...,
        description="Built context data; send it as `context` to POST /api/chat/execute",
    )
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

        # The turn runs under the session's lock: a concurrent turn must not
        # snapshot the thread before this one's answer is checkpointed.
        async with serialized_turn(full_session_id):
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
            from langchain_core.messages import HumanMessage

            # Explicit id so a failed turn can remove it from the checkpoint.
            user_message = HumanMessage(content=request.message, id=str(uuid4()))
            state_values["messages"].append(user_message)

            # Execute the chat graph. The node is async, so the run goes through
            # `ainvoke`; the graph's HybridSqliteSaver bridges the checkpoint
            # writes to the sync connection on a worker thread, so the event loop
            # is not blocked by them.
            # ainvoke_chat_turn also drops the question from the checkpoint when
            # the turn fails, so a retry doesn't add it twice.
            result = await ainvoke_chat_turn(
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


async def _stream_execute_chat(
    request: ExecuteChatRequest,
    http_request: Request,
    thread_id: str,
    session: Any,
    notebook: Optional[Notebook],
    model_override: Optional[str],
) -> AsyncGenerator[str, None]:
    """Stream one notebook-chat turn as SSE: `user_message` -> `token`… -> `complete`.

    Generation runs *inside* the chat graph (`graph.astream` with
    `stream_mode="messages"`), so the answer goes through the same node, prompt
    and checkpointer as the buffered endpoint, and future graph features apply
    to streamed turns too. The endpoint's only extras are the token envelope and
    the settlement on a turn that ends early: a stopped or timed-out turn keeps
    its partial answer, written as the node's output so the thread stays
    complete, and keeps the question when nothing was produced yet. Only a
    failed turn drops an unanswered question, so a retry does not stack it.

    Turns on one session are serialized by the session lock: a queued turn
    pings while it waits and snapshots only after the previous turn settled.
    """
    queue: "asyncio.Queue[Any]" = asyncio.Queue()
    outcome = StreamOutcome()
    parts: list[str] = []
    task: Optional["asyncio.Task[Any]"] = None
    question: Optional[HumanMessage] = None
    lock: Optional[asyncio.Lock] = None
    held = False
    persisted = False
    settled = False

    try:
        # A turn already in flight on this session is generating from the
        # thread as it was; queue behind it so this turn's snapshot includes
        # its answer. Keepalives cover the wait.
        lock = session_lock(thread_id)
        while True:
            try:
                await asyncio.wait_for(
                    lock.acquire(), timeout=_sse.KEEPALIVE_INTERVAL_SECONDS
                )
                held = True
                break
            except asyncio.TimeoutError:
                yield sse_keepalive()

        # Snapshot the thread before appending the new question.
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

        # Persist the question before generating: tokens reach the client long
        # before the graph would checkpoint, and a stop during prefill must not
        # lose what the user asked.
        await persist_pending_human_turn(
            chat_graph, thread_id, question, as_node=CHAT_NODE
        )
        persisted = True

        # The echo doubles as the acknowledgement that the question is
        # checkpointed: a client that has seen it never needs to restore the
        # message, even if it stops before the first token.
        yield sse({"type": "user_message", "content": request.message})

        task = asyncio.create_task(
            run_graph(
                queue,
                chat_graph,
                state_values,
                RunnableConfig(
                    configurable={"thread_id": thread_id, "model_id": model_override}
                ),
                CHAT_NODE,
                parts,
                ThinkingFilter(),
            )
        )
        async for frame in stream_events(
            queue, outcome, is_disconnected=http_request.is_disconnected
        ):
            yield frame

        content = "".join(parts)

        if outcome.kind == "done":
            # The node checkpoints its cleaned answer; take that rather than the
            # accumulated deltas so `complete` matches history exactly.
            final = await last_ai_content(chat_graph, thread_id)
            if not final.strip():
                raise IncompleteGenerationError(EMPTY_REPLY_MESSAGE)
            # Settled before the session save: a disconnect during that await
            # would otherwise let the teardown settle the answer a second time.
            settled = True
            await session.save()
            yield sse({"type": "complete", "content": final})
            return

        if outcome.kind == "timeout":
            # Stop the run before writing the partial answer: a still-running
            # graph could otherwise checkpoint afterwards and overwrite it.
            await stop_task(task)
            settled = await settle_turn_end(
                chat_graph,
                thread_id,
                content,
                question,
                as_node=CHAT_NODE,
                end=StreamEnd.TIMEOUT,
            )
            message = (
                f"The model did not finish within {int(_sse.MAX_STREAM_SECONDS)}s."
            )
            code: Optional[str] = "timeout"
            if content.strip():
                if settled:
                    message += " Partial answer kept."
                    code = "timeout_partial_kept"
                else:
                    message += " The partial answer could not be saved."
                    code = "timeout_partial_lost"
            yield format_error_event(IncompleteGenerationError(message), code=code)
            return

        if outcome.kind == "error":
            payload = outcome.payload
            if isinstance(payload, BaseException):
                logger.error(
                    f"Streamed chat turn failed in {thread_id}: {payload!r}\n"
                    f"  Traceback:\n{''.join(traceback.format_exception(payload))}"
                )
            # The worker only reports an error once `astream` has raised, so
            # the run is already finished here.
            settled = await settle_turn_end(
                chat_graph,
                thread_id,
                content,
                question,
                as_node=CHAT_NODE,
                end=StreamEnd.ERROR,
            )
            yield format_error_event(
                payload if isinstance(payload, BaseException) else RuntimeError(),
                suffix=(
                    "The partial answer could not be saved."
                    if content.strip() and not settled
                    else None
                ),
            )
            return

        # Disconnected: keep whatever arrived; the client is gone. Stop the run
        # before settling so it can't checkpoint over the partial answer. An
        # answerless stop keeps the question: it was accepted, just unanswered.
        await stop_task(task)
        settled = await settle_turn_end(
            chat_graph,
            thread_id,
            content,
            question,
            as_node=CHAT_NODE,
            end=StreamEnd.STOP,
        )

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
            # A cancellation lands here, not in the disconnect branch: the
            # question was accepted, so it stays even with no answer.
            await stop_task(task)
            settled = await settle_turn_end(
                chat_graph,
                thread_id,
                "".join(parts),
                question,
                as_node=CHAT_NODE,
                end=StreamEnd.STOP,
            )
        code = "empty_reply" if str(e) == EMPTY_REPLY_MESSAGE else None
        yield format_error_event(e, code=code)
    finally:

        async def _settle_if_needed() -> None:
            if persisted and question and not settled:
                await settle_turn_end(
                    chat_graph,
                    thread_id,
                    "".join(parts),
                    question,
                    as_node=CHAT_NODE,
                    end=StreamEnd.STOP,
                )

        await finalize_stream(task, _settle_if_needed)
        # Released only after the settlement is written, so the next turn
        # snapshots a settled thread.
        if held and lock is not None:
            lock.release()
            release_session_lock(thread_id)


@router.post("/chat/execute/stream")
async def execute_chat_stream(request: ExecuteChatRequest, http_request: Request):
    """Execute a chat request and stream the response as SSE.

    Additive sibling of `/chat/execute`, which stays for API consumers: same
    body, same graph, same persistence, but `text/event-stream` frames.
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
        # Nothing is streaming yet, so this has to be an HTTP response. The message
        # goes through the classifier (as the mid-stream errors do) so
        # provider/driver detail stays out of the client — but an unmatched
        # error may be internal (a database fault, say), and calling that an AI
        # service error would mislabel it, so it becomes a plain 500.
        exc_class, detail = classify_error(e)
        if exc_class is ExternalServiceError and detail.startswith("AI service error:"):
            raise OpenNotebookError("Could not start the chat stream.") from e
        raise exc_class(detail) from e


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
