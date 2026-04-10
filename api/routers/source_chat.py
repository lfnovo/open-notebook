import asyncio
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Source
from open_notebook.exceptions import (
    NotFoundError,
)
from open_notebook.graphs.source_chat import source_chat_graph as source_chat_graph
from open_notebook.utils.graph_utils import get_session_message_count

router = APIRouter()


# Helper functions for serialization
def serialize_source(source) -> dict:
    """Serialize a Source object to JSON-compatible dict."""
    if not source:
        return None
    
    try:
        result = {
            "id": str(source.id) if hasattr(source, "id") else None,
            "title": source.title if hasattr(source, "title") else None,
            "topics": source.topics if hasattr(source, "topics") else [],
        }
        
        # Add asset information
        if hasattr(source, "asset") and source.asset:
            result["asset"] = {
                "file_path": source.asset.file_path if hasattr(source.asset, "file_path") else None,
                "url": source.asset.url if hasattr(source.asset, "url") else None,
            }
        
        return result
    except Exception as e:
        logger.error(f"Error serializing source: {str(e)}")
        return None


def serialize_insights(insights) -> list:
    """Serialize a list of Insight objects to JSON-compatible list."""
    if not insights:
        return []
    
    result = []
    try:
        for insight in insights:
            insight_data = {
                "id": str(insight.id) if hasattr(insight, "id") else None,
                "type": insight.insight_type if hasattr(insight, "insight_type") else None,
                "content": insight.content if hasattr(insight, "content") else None,
            }
            result.append(insight_data)
    except Exception as e:
        logger.error(f"Error serializing insights: {str(e)}")
    
    return result


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
    suggested_questions: Optional[List[str]] = Field(
        None, description="Last suggested follow-up questions"
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

class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


@router.post(
    "/sources/{source_id}/chat/sessions", response_model=SourceChatSessionResponse
)
async def create_source_chat_session(
    request: CreateSourceChatSessionRequest,
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
                for msg in thread_state.values["messages"]:
                    messages.append(
                        ChatMessage(
                            id=getattr(msg, "id", f"msg_{len(messages)}"),
                            type=msg.type if hasattr(msg, "type") else "unknown",
                            content=msg.content
                            if hasattr(msg, "content")
                            else str(msg),
                            timestamp=None,  # LangChain messages don't have timestamps by default
                        )
                    )

            # Extract context indicators from the last state
            if "context_indicators" in thread_state.values:
                context_data = thread_state.values["context_indicators"]
                # Filter out None values to prevent Pydantic validation errors
                sources = [s for s in context_data.get("sources", []) if s is not None]
                insights = [i for i in context_data.get("insights", []) if i is not None]
                notes = [n for n in context_data.get("notes", []) if n is not None]
                context_indicators = ContextIndicator(
                    sources=sources,
                    insights=insights,
                    notes=notes,
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
            suggested_questions=getattr(session, "suggested_questions", None),
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source or session not found")
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
    session_id: str, source_id: str, message: str, model_override: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Stream the source chat response as Server-Sent Events."""
    try:
        # Get current state
        # Use sync get_state() in a thread since SqliteSaver doesn't support async
        current_state = await asyncio.to_thread(
            source_chat_graph.get_state,
            config=RunnableConfig(configurable={"thread_id": session_id}),
        )

        # Prepare state for execution
        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["source_id"] = source_id
        state_values["model_override"] = model_override

        # Add user message to state
        user_message = HumanMessage(content=message)
        state_values["messages"].append(user_message)

        # Send user message event
        user_event = {"type": "user_message", "content": message, "timestamp": None}
        yield f"data: {json.dumps(user_event)}\n\n"

        # Execute source chat graph synchronously (like notebook chat does)
        result = source_chat_graph.invoke(
            input=state_values,  # type: ignore[arg-type]
            config=RunnableConfig(
                configurable={"thread_id": session_id, "model_id": model_override}
            ),
        )

        # Stream AI response as single message (no chunking to avoid duplication)
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "type") and msg.type == "ai":
                    full_content = msg.content if hasattr(msg, "content") else str(msg)
                    ai_event = {
                        "type": "ai_message",
                        "content": full_content,
                        "timestamp": None,
                    }
                    yield f"data: {json.dumps(ai_event)}\n\n"

        # Stream context indicators with full details
        if "context_indicators" in result:
            context_event = {
                "type": "context_indicators",
                "data": result["context_indicators"],
            }
            yield f"data: {json.dumps(context_event)}\n\n"

        # Stream source details
        if "source" in result and result["source"]:
            source_detail_event = {
                "type": "source_details",
                "data": serialize_source(result["source"]),
            }
            yield f"data: {json.dumps(source_detail_event)}\n\n"

        # Stream insights details
        if "insights" in result and result["insights"]:
            insights_list = serialize_insights(result["insights"])
            if insights_list:
                insights_event = {
                    "type": "insights_details",
                    "data": insights_list,
                }
                yield f"data: {json.dumps(insights_event)}\n\n"

        # Stream entity details (person information, etc.)
        if "entity_details" in result and result["entity_details"]:
            entity_details_event = {
                "type": "entity_details",
                "data": result["entity_details"],
            }
            yield f"data: {json.dumps(entity_details_event)}\n\n"

        # Generate suggested questions grounded STRICTLY in the source document content
        try:
            import json as json_lib
            import re as re_lib
            from langchain_core.messages import SystemMessage as SysMsg
            from open_notebook.ai.provision import provision_langchain_model

            # Always fetch source fresh from DB to ensure valid id and full_text
            source_obj = await Source.get(source_id)

            source_full_text = ""
            source_title = ""
            source_insights_text = ""
            if source_obj and source_obj.id:
                source_full_text = (getattr(source_obj, "full_text", "") or "")
                source_title = getattr(source_obj, "title", "") or ""
                try:
                    insights = await source_obj.get_insights()
                    source_insights_text = "\n".join(
                        f"[{i.insight_type}]: {i.content[:800]}" for i in insights[:5]
                    )
                except Exception as ins_err:
                    logger.warning(f"[SOURCE-CHAT-SUGGEST] Could not load insights: {ins_err}")

            # Use full_text first 4000 chars + insights as context
            # If full_text is empty, use insights as primary context
            if source_full_text:
                source_context = (source_full_text[:4000] + "\n\n" + source_insights_text).strip()
            else:
                source_context = source_insights_text.strip()

            if not source_context:
                logger.warning(f"[SOURCE-CHAT-SUGGEST] No source content available for {source_id}")
                questions_list = []
            else:
                logger.info(f"[SOURCE-CHAT-SUGGEST] Generating questions from {len(source_context)} chars of source: {source_title}")

                prompt_text = f"""You are analyzing a specific source document. Read it carefully and generate 3 follow-up questions.

SOURCE DOCUMENT TITLE: {source_title}

SOURCE DOCUMENT CONTENT:
{source_context}

TASK: Generate exactly 3 short questions that:
1. Are DIRECTLY based on specific facts, names, events, or details in the document above
2. Are 5-8 words maximum each
3. Start with: Who/When/Where/How/Which/Why/What
4. Reference actual names, dates, places, or events from the document
5. Are different from what was already asked

ALREADY ASKED: {message}

CRITICAL: Every question MUST be answerable from the document content above. Do NOT invent or use external knowledge.

Return ONLY a valid JSON array of 3 strings. No explanation, no markdown.
Example format: ["Who is X?", "When did Y happen?", "Which gang did Z join?"]

JSON array:"""

                model = await provision_langchain_model(prompt_text, model_override, "chat", max_tokens=300, temperature=0.3)
                llm_response = model.invoke([SysMsg(content=prompt_text)])
                response_text = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
                logger.info(f"[SOURCE-CHAT-SUGGEST] LLM raw response: {response_text[:300]}")

                questions = None
                # Strategy 1: direct JSON parse
                try:
                    questions = json_lib.loads(response_text.strip())
                except json_lib.JSONDecodeError:
                    pass
                # Strategy 2: strip markdown fences
                if not questions:
                    cleaned = re_lib.sub(r'```(?:json)?\s*', '', response_text).replace('```', '').strip()
                    try:
                        questions = json_lib.loads(cleaned)
                    except json_lib.JSONDecodeError:
                        pass
                # Strategy 3: extract [...] block
                if not questions:
                    match = re_lib.search(r'\[[\s\S]*?\]', response_text)
                    if match:
                        try:
                            questions = json_lib.loads(match.group())
                        except json_lib.JSONDecodeError:
                            pass
                # Strategy 4: extract quoted question strings
                if not questions or not isinstance(questions, list) or len(questions) < 2:
                    extracted = re_lib.findall(r'"([^"]{5,}[?])"', response_text)
                    if len(extracted) >= 2:
                        questions = extracted

                questions_list: list[str] = []
                if questions and isinstance(questions, list):
                    questions_list = [
                        q.strip() for q in questions
                        if isinstance(q, str) and q.strip() and len(q.strip()) > 4 and '?' in q
                    ][:3]

                # Enforce max 10 words per question
                def trim_question(q: str, max_words: int = 10) -> str:
                    words = q.split()
                    if len(words) <= max_words:
                        return q
                    return " ".join(words[:max_words]).rstrip(".,;:") + "?"

                questions_list = [trim_question(q) for q in questions_list]

                # Source-grounded fallback using actual names from document/insights
                if len(questions_list) < 3:
                    # Extract from source_context (includes insights when full_text is empty)
                    extract_text = source_context[:3000]
                    names = re_lib.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b', extract_text)
                    unique_names = list(dict.fromkeys(names))
                    dates = re_lib.findall(r'\b(?:19|20)\d{2}\b', extract_text)
                    unique_dates = list(dict.fromkeys(dates))
                    places = re_lib.findall(r'\b(?:Rajasthan|Delhi|Punjab|Haryana|Bihar|UP|Sikar|Jaipur|Mumbai|Bikaner|Nagaur)\b', extract_text)
                    unique_places = list(dict.fromkeys(places))
                    gangs = re_lib.findall(r'\b(?:Bishnoi|Jathedi|Gogi|Banuda|Lawrence)\s+(?:Gang|Group|gang|group)?\b', extract_text)
                    unique_gangs = list(dict.fromkeys(gangs))

                    fallback = []
                    if unique_names and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"Who is {unique_names[0]}?")
                    if len(unique_names) > 1 and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"How is {unique_names[0]} linked to {unique_names[1]}?")
                    if unique_gangs and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"What is the {unique_gangs[0].strip()} role?")
                    if unique_dates and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"What happened in {unique_dates[0]}?")
                    if unique_places and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"What activities occurred in {unique_places[0]}?")
                    if len(unique_names) > 2 and len(questions_list) + len(fallback) < 3:
                        fallback.append(f"What crimes involve {unique_names[2]}?")

                    for fb in fallback:
                        if len(questions_list) >= 3:
                            break
                        questions_list.append(fb)

                questions_list = questions_list[:3]
                logger.info(f"[SOURCE-CHAT-SUGGEST] Final {len(questions_list)} questions: {questions_list}")

            # Persist to session
            full_session_id_for_save = session_id if session_id.startswith("chat_session:") else f"chat_session:{session_id}"
            session_obj = await ChatSession.get(full_session_id_for_save)
            if session_obj and questions_list:
                session_obj.suggested_questions = questions_list
                await session_obj.save()

            if questions_list:
                yield f"data: {json.dumps({'type': 'suggested_questions', 'questions': questions_list})}\n\n"

        except Exception as sq_err:
            logger.error(f"Error generating suggested questions for source chat: {str(sq_err)}")

        # Send completion signal
        completion_event = {"type": "complete"}
        yield f"data: {json.dumps(completion_event)}\n\n"

    except Exception as e:
        from open_notebook.utils.error_classifier import classify_error

        _, user_message = classify_error(e)
        logger.error(f"Error in source chat streaming: {str(e)}")
        error_event = {"type": "error", "message": user_message}
        yield f"data: {json.dumps(error_event)}\n\n"


@router.post("/sources/{source_id}/chat/sessions/{session_id}/messages")
async def send_message_to_source_chat(
    request: SendMessageRequest,
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

        # Update session timestamp
        await session.save()

        # Return streaming response
        return StreamingResponse(
            stream_source_chat_response(
                session_id=full_session_id,
                source_id=full_source_id,
                message=request.message,
                model_override=model_override,
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to source chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")
