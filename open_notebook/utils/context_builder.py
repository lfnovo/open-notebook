"""Context building for chat and podcast generation.

This is the single implementation behind:

- ``POST /api/chat/context`` (`api/routers/chat.py`) — assembles notebook
  context from a source/note inclusion config, via
  :func:`build_notebook_context`.
- the source-chat graph (`open_notebook/graphs/source_chat.py`) — assembles
  a single source plus its insights under a token budget, via
  :func:`build_source_context`.

The inclusion config uses string matching on human-readable status values
("not in context", "insights", "full content"). That protocol is shared with
the frontend — do not change it here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from loguru import logger

from open_notebook.domain.notebook import (
    Note,
    Notebook,
    Source,
    SourceInsight,
)
from open_notebook.exceptions import DatabaseOperationError, NotFoundError

from .token_utils import token_count


def _ensure_prefix(table: str, record_id: str) -> str:
    """Ensure a record ID carries its table prefix (`table:id`)."""
    prefix = f"{table}:"
    return record_id if record_id.startswith(prefix) else f"{prefix}{record_id}"


async def build_notebook_context(
    notebook: Notebook,
    context_config: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, list], str]:
    """Assemble source/note context for a notebook.

    With a config, each entry's status string decides inclusion: "not in"
    skips it, "insights" includes the short source context, "full content"
    includes the long context (notes only support "full content"). Without a
    config, every source and note is included with its short context.

    Failures on individual items are logged and skipped — one broken record
    never fails the whole request.

    Returns:
        ({"sources": [...], "notes": [...]}, concatenated str() of every
        included context dict — used for token/char counting).
    """
    context_data: Dict[str, list] = {"sources": [], "notes": []}
    total_content = ""

    if context_config:
        for source_id, status in context_config.get("sources", {}).items():
            if "not in" in status:
                continue

            try:
                full_source_id = _ensure_prefix("source", source_id)

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

        for note_id, status in context_config.get("notes", {}).items():
            if "not in" in status:
                continue

            try:
                full_note_id = _ensure_prefix("note", note_id)
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
        try:
            insights_by_source = await SourceInsight.get_for_sources(
                [source.id for source in sources if source.id]
            )
        except Exception as e:
            # Match the per-source fallback below: a hiccup fetching
            # insights shouldn't fail the whole context request.
            logger.warning(f"Error batch-fetching source insights: {str(e)}")
            insights_by_source = {}
        for source in sources:
            try:
                source_context = await source.get_context(
                    context_size="short",
                    insights=insights_by_source.get(source.id or "", []),
                )
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

    return context_data, total_content


async def build_source_context(
    source_id: str, max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """Assemble a single source's full content plus its insights.

    Used by the source-chat graph. Uses the "long" context so the source's
    full text is always included — a source with no insights/transformations
    would otherwise leave the LLM with only the title. If `max_tokens` is
    given, insights are dropped (last-fetched first) until the total fits.
    The source itself is never dropped — a large full_text can alone exceed
    the budget, and dropping it would leave an empty context; the caller
    (source-chat's prompt formatter) already caps full_text at a fixed size
    before it reaches the LLM.

    Returns a dict with "sources", "notes" (always empty), "insights",
    "total_tokens", "total_items" and per-type counts in "metadata".
    """
    try:
        sources: list = []
        insights: list = []
        item_tokens: list[int] = []

        try:
            full_source_id = _ensure_prefix("source", source_id)
            source = await Source.get(full_source_id)
        except NotFoundError:
            source = None

        if source:
            source_context = await source.get_context(context_size="long")
            sources.append(source_context)
            item_tokens.append(token_count(str(source_context)))

            for insight in await source.get_insights():
                insight_content = {
                    "id": insight.id,
                    "source_id": source.id,
                    "insight_type": insight.insight_type,
                    "content": insight.content,
                }
                insights.append(insight_content)
                item_tokens.append(token_count(str(insight_content)))
        else:
            logger.warning(f"Source {source_id} not found")

        # Truncate to the token budget: drop insights from the end. The
        # source is never dropped, even if it alone exceeds the budget —
        # an empty context is worse than a source whose full_text gets
        # capped later by the prompt formatter (see docstring). If the
        # source alone already exceeds the budget, trimming insights can't
        # bring the total under it anyway, so keep them all instead of
        # discarding useful context for nothing.
        total_tokens = sum(item_tokens)
        source_tokens = item_tokens[0] if sources else 0
        if max_tokens is not None:
            while (
                total_tokens > max_tokens
                and insights
                and source_tokens <= max_tokens
            ):
                total_tokens -= item_tokens.pop()
                insights.pop()

        total_items = len(sources) + len(insights)
        logger.info(f"Built context with {total_items} items, {total_tokens} tokens")

        return {
            "sources": sources,
            "notes": [],
            "insights": insights,
            "total_tokens": total_tokens,
            "total_items": total_items,
            "metadata": {
                "source_count": len(sources),
                "note_count": 0,
                "insight_count": len(insights),
            },
        }
    except Exception as e:
        logger.error(f"Error building context: {str(e)}")
        raise DatabaseOperationError(f"Failed to build context: {str(e)}")
