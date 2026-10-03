"""Shared helpers for the chat and source-chat routers.

Both `api/routers/chat.py` and `api/routers/source_chat.py` operate on
`chat_session` records linked to their parent (notebook or source) via the
`refers_to` relation, and both convert LangGraph state messages into API
response models. This module holds the single definition of those pieces.

Behavior notes:
- The helpers raise exactly what the previously inlined blocks raised
  (`NotFoundError` propagates from `ObjectModel.get`, `HTTPException(404)` for
  a missing relation), so each router's existing try/except arms keep mapping
  them to the same status codes and messages as before.
"""

from typing import Any, Iterable, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, Field

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import ChatSession, Source


# Shared response models
class ChatMessage(BaseModel):
    id: str = Field(..., description="Message ID")
    type: str = Field(..., description="Message type (human|ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


def normalize_record_id(table: str, record_id: str) -> str:
    """Ensure a record ID carries its table prefix (`table:id`)."""
    prefix = f"{table}:"
    return record_id if record_id.startswith(prefix) else f"{prefix}{record_id}"


async def get_source_or_404(source_id: str) -> Tuple[str, Source]:
    """Normalize a source ID and fetch the source, 404 if missing."""
    full_source_id = normalize_record_id("source", source_id)
    source = await Source.get(full_source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return full_source_id, source


async def get_session_or_404(session_id: str) -> Tuple[str, ChatSession]:
    """Normalize a session ID and fetch the chat session, 404 if missing."""
    full_session_id = normalize_record_id("chat_session", session_id)
    session = await ChatSession.get(full_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return full_session_id, session


async def get_verified_source_session(
    source_id: str, session_id: str
) -> Tuple[str, Source, str, ChatSession]:
    """Verify the source exists, the session exists, and the session refers to
    the source. Returns the normalized IDs plus both records."""
    full_source_id, source = await get_source_or_404(source_id)
    full_session_id, session = await get_session_or_404(session_id)

    relation_query = await repo_query(
        "SELECT * FROM refers_to WHERE in = $session_id AND out = $source_id",
        {
            "session_id": ensure_record_id(full_session_id),
            "source_id": ensure_record_id(full_source_id),
        },
    )
    if not relation_query:
        raise HTTPException(status_code=404, detail="Session not found for this source")

    return full_source_id, source, full_session_id, session


def extract_chat_messages(raw_messages: Iterable[Any]) -> List[ChatMessage]:
    """Convert LangGraph/LangChain state messages into `ChatMessage` models."""
    messages: List[ChatMessage] = []
    for msg in raw_messages:
        messages.append(
            ChatMessage(
                id=getattr(msg, "id", f"msg_{len(messages)}"),
                type=msg.type if hasattr(msg, "type") else "unknown",
                content=msg.content if hasattr(msg, "content") else str(msg),
                timestamp=None,  # LangChain messages don't have timestamps by default
            )
        )
    return messages
