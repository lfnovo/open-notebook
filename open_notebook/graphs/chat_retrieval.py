"""Smart-chat retrieval: notebook-scoped RAG for the Chat feature.

Chat is scoped to a single notebook (unlike Ask, which searches the whole
library). Instead of injecting the full text of every selected source — which
explodes context for large libraries — this module, per user message:

  1. rewrites the message (+ recent history) into several search queries,
  2. vector-searches each query scoped to the notebook's ``Auto`` sources,
  3. merges/dedupes the hits and caps them to a token-ish budget,
  4. formats them (with document ids for citations) into a context string.

The endpoint combines this with any ``Full`` (pinned, verbatim) sources. The LLM
call (query rewrite) and the pure assembly helpers are deliberately separated so
the assembly logic can be unit-tested without a model or a database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import vector_search
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.text_utils import extract_text_content

# How many hits to pull per individual query before merging.
PER_QUERY_LIMIT = 8
# How many merged hits to keep in the final context (rough proxy for a token cap).
DEFAULT_TOP_K = 15
# How many recent turns of conversation to feed the query rewriter.
HISTORY_TURNS = 6


class RewrittenQueries(BaseModel):
    queries: List[str] = Field(default_factory=list)


def format_history(messages: List[Any], turns: int = HISTORY_TURNS) -> str:
    """Render the last ``turns`` messages as 'Role: text' lines for the rewriter.

    Accepts LangChain message objects or plain dicts with ``type``/``role`` and
    ``content``. Returns "" when there is nothing prior.
    """
    if not messages:
        return ""
    recent = messages[-turns:]
    lines: List[str] = []
    for m in recent:
        role = (
            getattr(m, "type", None)
            or (m.get("type") if isinstance(m, dict) else None)
            or (m.get("role") if isinstance(m, dict) else None)
            or "user"
        )
        content = (
            getattr(m, "content", None)
            if not isinstance(m, dict)
            else m.get("content", "")
        )
        content = extract_text_content(content) if content is not None else ""
        content = str(content).strip()
        if not content:
            continue
        label = {"human": "User", "ai": "Assistant"}.get(str(role), str(role).title())
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


def merge_and_cap(results_per_query: List[List[dict]], cap: int = DEFAULT_TOP_K) -> List[dict]:
    """Merge hits from several queries, dedupe by document id (keeping the highest
    similarity), sort by similarity desc, and cap the count.

    Pure function — no I/O — so it is directly unit-testable.
    """
    best: Dict[str, dict] = {}
    for results in results_per_query:
        for hit in results or []:
            hid = str(hit.get("id"))
            if not hid or hid == "None":
                continue
            sim = float(hit.get("similarity") or 0)
            existing = best.get(hid)
            if existing is None or sim > float(existing.get("similarity") or 0):
                best[hid] = hit
    ordered = sorted(
        best.values(), key=lambda h: float(h.get("similarity") or 0), reverse=True
    )
    return ordered[:cap]


def format_retrieved(hits: List[dict]) -> str:
    """Format merged hits into a context string with document ids for citation.

    Pure function. ``matches`` may be a list of chunk strings or a single string.
    """
    if not hits:
        return ""
    blocks: List[str] = []
    for hit in hits:
        hid = str(hit.get("id"))
        title = str(hit.get("title") or "").strip()
        matches = hit.get("matches")
        if isinstance(matches, list):
            text = "\n".join(str(m).strip() for m in matches if str(m).strip())
        else:
            text = str(matches or "").strip()
        header = f"## [{hid}]" + (f" {title}" if title else "")
        blocks.append(f"{header}\n\n{text}".strip())
    return "\n\n".join(blocks)


async def generate_queries(
    message: str, history: str, model_id: Optional[str] = None
) -> List[str]:
    """Rewrite the message + history into search queries via the tools model.

    Always includes the raw message as a fallback query, so retrieval degrades
    gracefully (never empty) if the model returns nothing usable.
    """
    fallback = [message.strip()] if message and message.strip() else []
    try:
        parser = PydanticOutputParser(pydantic_object=RewrittenQueries)
        prompt = Prompter(prompt_template="chat_retrieval/queries", parser=parser).render(  # type: ignore[arg-type]
            data={"message": message, "history": history}
        )
        model = await provision_langchain_model(
            prompt, model_id, "tools", max_tokens=500, structured=dict(type="json")
        )
        ai_message = await model.ainvoke(prompt)
        cleaned = clean_thinking_content(extract_text_content(ai_message.content))
        parsed = parser.parse(cleaned)
        queries = [q.strip() for q in parsed.queries if q and q.strip()]
    except Exception as e:
        # Retrieval must be resilient: a rewrite failure falls back to the raw
        # message rather than breaking the whole chat turn.
        logger.warning(f"Query rewrite failed, falling back to raw message: {e}")
        queries = []
    # Dedupe while preserving order, and guarantee the raw message is present.
    seen = set()
    out: List[str] = []
    for q in queries + fallback:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out[:5]


async def retrieve_context(
    message: str,
    history_messages: List[Any],
    source_ids: List[str],
    *,
    model_id: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
    minimum_score: float = 0.2,
) -> Dict[str, Any]:
    """Run notebook-scoped retrieval for one chat turn.

    Returns ``{"context": str, "queries": [...], "chunk_count": int,
    "source_ids": [...]}``. ``source_ids`` bounds the search to the notebook's
    Auto sources; an empty list means "nothing to retrieve" and yields an empty
    context (the caller decides how to handle that).
    """
    if not source_ids or not (message and message.strip()):
        return {"context": "", "queries": [], "chunk_count": 0, "source_ids": []}

    history = format_history(history_messages)
    queries = await generate_queries(message, history, model_id)

    results_per_query: List[List[dict]] = []
    for q in queries:
        try:
            hits = await vector_search(
                q,
                PER_QUERY_LIMIT,
                source=True,
                note=False,
                minimum_score=minimum_score,
                source_ids=source_ids,
            )
            results_per_query.append(hits or [])
        except Exception as e:
            logger.warning(f"vector_search failed for query '{q}': {e}")

    merged = merge_and_cap(results_per_query, top_k)
    return {
        "context": format_retrieved(merged),
        "queries": queries,
        "chunk_count": len(merged),
        "source_ids": source_ids,
    }
