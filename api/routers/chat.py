import asyncio
import json
import traceback
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
# from loguru import logger
from pydantic import BaseModel, Field
import logging as logger
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Note, Notebook, Source
from open_notebook.exceptions import (
    NotFoundError,
)
from open_notebook.graphs.chat import graph as chat_graph, stream_model_tokens
from open_notebook.utils.graph_utils import get_session_message_count

router = APIRouter()


def _fallback_suggested_questions(user_message: str, ai_response: str) -> list[str]:
    """Return safe fallback follow-up questions when LLM parsing fails."""
    prompt = (user_message or "").strip().rstrip("?.!")
    if not prompt:
        return [
            "Can you summarize this in simple terms?",
            "What are the most important points here?",
            "What should I ask next to go deeper?",
        ]

    topic = prompt[:80]
    return [
        f"Can you summarize the key points about {topic}?",
        f"What evidence or sources support this about {topic}?",
        f"What should I explore next about {topic}?",
    ]


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


class ChatSessionWithMessagesResponse(ChatSessionResponse):
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Session messages"
    )
    suggested_questions: Optional[List[str]] = Field(
        None, description="Last suggested follow-up questions"
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
    suggested_questions: Optional[List[str]] = Field(
        None, description="Suggested follow-up questions"
    )


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

        # Get session state from LangGraph to retrieve messages
        # Use sync get_state() in a thread since SqliteSaver doesn't support async
        thread_state = await asyncio.to_thread(
            chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": full_session_id}),
        )

        # Extract messages from state
        messages: list[ChatMessage] = []
        if thread_state and thread_state.values and "messages" in thread_state.values:
            for msg in thread_state.values["messages"]:
                messages.append(
                    ChatMessage(
                        id=getattr(msg, "id", f"msg_{len(messages)}"),
                        type=msg.type if hasattr(msg, "type") else "unknown",
                        content=msg.content if hasattr(msg, "content") else str(msg),
                        timestamp=None,  # LangChain messages don't have timestamps by default
                    )
                )

        # Find notebook_id (we need to query the relationship)
        # Ensure session_id has proper table prefix
        full_session_id = (
            session_id
            if session_id.startswith("chat_session:")
            else f"chat_session:{session_id}"
        )

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
            suggested_questions=getattr(session, "suggested_questions", None),
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error fetching session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching session: {str(e)}")


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
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
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")


@router.delete("/chat/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: str):
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

        await session.delete()

        return SuccessResponse(success=True, message="Session deleted successfully")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@router.post("/chat/execute", response_model=ExecuteChatResponse)
async def execute_chat(request: ExecuteChatRequest):
    """Execute a chat request and get AI response."""
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
        state_values["model_override"] = model_override

        # Add user message to state
        from langchain_core.messages import HumanMessage

        user_message = HumanMessage(content=request.message)
        state_values["messages"].append(user_message)

        # Execute chat graph
        result = chat_graph.invoke(
            input=state_values,  # type: ignore[arg-type]
            config=RunnableConfig(
                configurable={
                    "thread_id": full_session_id,
                    "model_id": model_override,
                }
            ),
        )

        # Update session timestamp
        await session.save()

        # Convert messages to response format
        messages: list[ChatMessage] = []
        for msg in result.get("messages", []):
            messages.append(
                ChatMessage(
                    id=getattr(msg, "id", f"msg_{len(messages)}"),
                    type=msg.type if hasattr(msg, "type") else "unknown",
                    content=msg.content if hasattr(msg, "content") else str(msg),
                    timestamp=None,
                )
            )

        return ExecuteChatResponse(
            session_id=request.session_id, 
            messages=messages,
            suggested_questions=None
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        # Log detailed error with context for debugging
        logger.error(
            f"Error executing chat: {str(e)}\n"
            f"  Session ID: {request.session_id}\n"
            f"  Model override: {request.model_override}\n"
            f"  Traceback:\n{traceback.format_exc()}"
        )
        raise HTTPException(status_code=500, detail=f"Error executing chat: {str(e)}")


@router.post("/chat/stream-execute")
async def stream_execute_chat(request: ExecuteChatRequest):
    """Execute a chat request with token streaming (Server-Sent Events)."""
    try:
        # Verify session exists
        full_session_id = (
            request.session_id
            if request.session_id.startswith("chat_session:")
            else f"chat_session:{request.session_id}"
        )
        session = await ChatSession.get(full_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Determine model override
        model_override = (
            request.model_override
            if request.model_override is not None
            else getattr(session, "model_override", None)
        )

        # Get current state
        current_state = await asyncio.to_thread(
            chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": full_session_id}),
        )

        # Prepare state for execution
        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["context"] = request.context
        state_values["model_override"] = model_override

        # Add user message to state
        user_message = HumanMessage(content=request.message)
        state_values["messages"].append(user_message)

        # ✅ Save user message to graph state for persistence before streaming
        await asyncio.to_thread(
            chat_graph.update_state,
            config=RunnableConfig(
                configurable={
                    "thread_id": full_session_id,
                    "model_id": model_override,
                }
            ),
            values={"messages": user_message},  # Persist user message
        )

        async def generate_stream() -> AsyncIterator[str]:
            """Generator function that streams tokens from the model."""
            accumulated_response = ""
            token_count = 0
            try:
                logger.info(f"[API-STREAM] Starting stream for session: {full_session_id}, model: {model_override}")
                
                # Stream tokens from model
                async for token in stream_model_tokens(
                    state_values["messages"], model_override, state_values
                ):
                    accumulated_response += token
                    token_count += 1
                    
                    # Send token as SSE with explicit formatting
                    data = json.dumps({'token': token})
                    sse_line = f"data: {data}\n\n"
                    
                    logger.debug(f"[API-STREAM] Sending token #{token_count}: {repr(token[:30])}")
                    yield sse_line
                    
                    # Critical: Force immediate flush to prevent buffering
                    # This ensures tokens are sent to client ASAP
                    await asyncio.sleep(0)

                logger.info(f"[API-STREAM] Streaming complete. Total tokens: {token_count}")

                # After streaming completes, save the AI message to the graph state
                from langchain_core.messages import AIMessage

                ai_message = AIMessage(content=accumulated_response)
                
                # Save to graph state for persistence
                await asyncio.to_thread(
                    chat_graph.update_state,
                    config=RunnableConfig(
                        configurable={
                            "thread_id": full_session_id,
                            "model_id": model_override,
                        }
                    ),
                    values={"messages": ai_message},  # type: ignore[arg-type]
                )

                # Update session timestamp
                await session.save()

                # Generate suggested follow-up questions
                try:
                    logger.info("[API-STREAM] ⚡ STARTING QUESTION GENERATION...")
                    
                    # Get the original user message
                    user_msg = None
                    for msg in state_values["messages"]:
                        if hasattr(msg, 'type') and msg.type == 'human':
                            user_msg = msg.content
                            break
                    
                    logger.debug(f"[API-STREAM] 📝 User message: {user_msg[:100] if user_msg else 'NONE'}")
                    logger.debug(f"[API-STREAM] 🤖 AI response length: {len(accumulated_response)}")
                    
                    # Build prompt for generating questions directly (without ai_prompter dependency)
                    prompt_text = f"""Based on the conversation below, generate 3 insightful follow-up questions that the user might want to ask next.

User Question: {user_msg or request.message}

AI Response: {accumulated_response[:1000]}

Requirements:
- Generate exactly 3 questions
- Questions should be natural follow-ups to the current conversation
- Keep questions concise and clear (under 15 words each)
- Return ONLY a valid JSON array - nothing else, no markdown blocks

Return ONLY this format (no code blocks, no explanation):
["First question here?", "Second question here?", "Third question here?"]"""
                    
                    logger.debug(f"[API-STREAM] 📋 Prompt prepared: {len(prompt_text)} chars")
                    
                    # Generate questions using LLM
                    from open_notebook.ai.provision import provision_langchain_model
                    model = await provision_langchain_model(
                        prompt_text,
                        model_override,
                        "chat",
                        max_tokens=200
                    )
                    
                    logger.debug(f"[API-STREAM] 🎯 Model provisioned: {model_override}")
                    
                    from langchain_core.messages import SystemMessage
                    response = model.invoke([SystemMessage(content=prompt_text)])
                    
                    # Parse the response as JSON array of questions
                    import json as json_lib
                    try:
                        # Extract JSON from response
                        response_text = response.content if hasattr(response, 'content') else str(response)
                        logger.info(f"[API-STREAM] 📤 Raw LLM response:\n{response_text}")
                        
                        # Try multiple parsing strategies
                        questions = None
                        
                        # Strategy 1: Direct JSON array
                        try:
                            questions = json_lib.loads(response_text.strip())
                            logger.info("[API-STREAM] ✅ Strategy 1: Direct JSON parse SUCCESS")
                        except json_lib.JSONDecodeError as e:
                            logger.debug(f"[API-STREAM] ❌ Strategy 1 failed: {str(e)[:100]}")
                            pass
                        
                        # Strategy 2: JSON array with markdown code blocks
                        if not questions:
                            import re
                            # Remove markdown code blocks
                            cleaned = re.sub(r'```(?:json)?\n?', '', response_text)
                            cleaned = cleaned.strip()
                            logger.debug(f"[API-STREAM] 🧹 Strategy 2 cleaned: {cleaned[:100]}")
                            try:
                                questions = json_lib.loads(cleaned)
                                logger.info("[API-STREAM] ✅ Strategy 2: Markdown-cleaned parse SUCCESS")
                            except json_lib.JSONDecodeError as e:
                                logger.debug(f"[API-STREAM] ❌ Strategy 2 failed: {str(e)[:100]}")
                                pass
                        
                        # Strategy 3: Find JSON array pattern
                        if not questions:
                            json_match = re.search(r'\[\s*["\'].*?["\'][^\]]*\]', response_text, re.DOTALL)
                            if json_match:
                                logger.debug(f"[API-STREAM] 🔍 Strategy 3 matched: {json_match.group()[:100]}")
                                try:
                                    questions = json_lib.loads(json_match.group())
                                    logger.info("[API-STREAM] ✅ Strategy 3: Regex pattern parse SUCCESS")
                                except json_lib.JSONDecodeError as e:
                                    logger.debug(f"[API-STREAM] ❌ Strategy 3 failed: {str(e)[:100]}")
                                    pass
                            else:
                                logger.debug("[API-STREAM] 🔍 Strategy 3: No regex match found")
                        
                        questions_list: list[str] = []
                        if questions and isinstance(questions, list) and len(questions) > 0:
                            # Filter to valid questions (non-empty strings)
                            questions_list = [
                                q.strip() for q in questions if isinstance(q, str) and q.strip()
                            ][:3]

                            if not questions_list:
                                logger.warning(
                                    f"[API-STREAM] ⚠️ No valid questions after filtering. Got: {questions}"
                                )
                        else:
                            logger.warning(
                                f"[API-STREAM] ⚠️ Could not parse questions. Got: {type(questions)} - {str(questions)[:200] if questions else 'null'}"
                            )

                        # Fallback if parser/model returned invalid output
                        if not questions_list:
                            questions_list = _fallback_suggested_questions(
                                user_msg or request.message, accumulated_response
                            )
                            logger.info(
                                f"[API-STREAM] ♻️ Using fallback suggested questions: {questions_list}"
                            )

                        # ✅ Save suggested questions to session for persistence
                        session.suggested_questions = questions_list
                        await session.save()
                        logger.info("[API-STREAM] 💾 Saved questions to session")

                        # Send suggested questions as SSE
                        questions_data = {
                            "type": "suggested_questions",
                            "questions": questions_list,
                        }
                        yield f"data: {json_lib.dumps(questions_data)}\n\n"
                        logger.info(
                            f"[API-STREAM] 📡 Sent {len(questions_list)} questions to client via SSE"
                        )
                    except Exception as parse_err:
                        logger.error(f"[API-STREAM] ❌ Error parsing questions: {str(parse_err)}", exc_info=True)
                        # Send fallback suggestions even when parsing fails unexpectedly
                        fallback_questions = _fallback_suggested_questions(
                            user_msg or request.message, accumulated_response
                        )
                        session.suggested_questions = fallback_questions
                        await session.save()
                        yield f"data: {json.dumps({'type': 'suggested_questions', 'questions': fallback_questions})}\n\n"
                
                except Exception as e:
                    logger.error(f"[API-STREAM] ❌ Error generating suggested questions: {str(e)}", exc_info=True)
                    # Send fallback suggestions even when generation fails
                    fallback_questions = _fallback_suggested_questions(
                        request.message, accumulated_response
                    )
                    session.suggested_questions = fallback_questions
                    await session.save()
                    yield f"data: {json.dumps({'type': 'suggested_questions', 'questions': fallback_questions})}\n\n"

                # Send completion signal with final stats
                completion_data = {
                    'done': True, 
                    'total_length': len(accumulated_response),
                    'total_tokens': token_count
                }
                yield f"data: {json.dumps(completion_data)}\n\n"

            except Exception as e:
                logger.error(f"[API-STREAM] Error during streaming: {str(e)}\n{traceback.format_exc()}")
                error_data = {'error': str(e), 'total_tokens': token_count}
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
            },
        )

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error in stream_execute_chat: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error executing chat: {str(e)}")


@router.post("/chat/context", response_model=BuildContextResponse)
async def build_context(request: BuildContextRequest):
    """Build context for a notebook based on context configuration."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        context_data: dict[str, list[dict[str, str]]] = {"sources": [], "notes": []}
        total_content = ""

        # Process context configuration if provided
        if request.context_config:
            # Process sources
            for source_id, status in request.context_config.get("sources", {}).items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_source_id = (
                        source_id
                        if source_id.startswith("source:")
                        else f"source:{source_id}"
                    )

                    try:
                        source = await Source.get(full_source_id)
                    except Exception:
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
                    full_note_id = (
                        note_id if note_id.startswith("note:") else f"note:{note_id}"
                    )
                    note = await Note.get(full_note_id)
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
            sources = await notebook.get_sources()
            for source in sources:
                try:
                    source_context = await source.get_context(context_size="short")
                    context_data["sources"].append(source_context)
                    total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source.id}: {str(e)}")
                    continue

            notes = await notebook.get_notes()
            for note in notes:
                try:
                    note_context = note.get_context(context_size="short")
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
