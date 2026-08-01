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

import re
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

SOURCE_TRUNCATION_NOTICE = (
    "\n\n[Source content truncated to fit the context token budget.]"
)
SOURCE_INSIGHT_BUDGET_RATIO = 0.2


def _ensure_prefix(table: str, record_id: str) -> str:
    """Ensure a record ID carries its table prefix (`table:id`)."""
    prefix = f"{table}:"
    return record_id if record_id.startswith(prefix) else f"{prefix}{record_id}"


def _truncate_source_to_token_budget(
    source_context: Dict[str, Any],
    max_tokens: int,
) -> tuple[Optional[Dict[str, Any]], bool]:
    """Truncate source text to a token budget while retaining source metadata.

    The longest fitting token-aligned prefix is retained without assuming that
    BPE token counts grow monotonically with character length. The truncation
    notice is part of the budget so downstream formatters never need a second
    size policy.

    Args:
        source_context: Long source context containing ``full_text``.
        max_tokens: Maximum tokens available for the serialized source context.

    Returns:
        The budgeted source context (or ``None`` when even an explicit notice
        cannot fit) and whether its text was truncated.
    """
    if token_count(str(source_context)) <= max_tokens:
        return source_context, False

    full_text = source_context.get("full_text")
    if not isinstance(full_text, str) or not full_text.strip():
        return None, False

    def candidate(prefix: str) -> Dict[str, Any]:
        return {
            **source_context,
            "full_text": prefix + SOURCE_TRUNCATION_NOTICE,
        }

    # A very small budget may not even fit source metadata plus the notice.
    # Omit the item; the caller records an explicit status in context metadata.
    notice_only = candidate("")
    if token_count(str(notice_only)) > max_tokens:
        return None, True

    try:
        import tiktoken

        encoding = tiktoken.get_encoding("o200k_base")
        source_tokens = encoding.encode(full_text, disallowed_special=())

        # Examine token prefixes from longest to shortest. Unlike a character
        # binary search, this remains correct when a BPE merge makes a longer
        # character prefix use fewer tokens than a shorter one.
        for prefix_token_count in range(
            min(len(source_tokens), max_tokens),
            0,
            -1,
        ):
            prefix = encoding.decode_bytes(
                source_tokens[:prefix_token_count]
            ).decode("utf-8", errors="ignore")
            if not prefix:
                continue
            truncated = candidate(prefix)
            if token_count(str(truncated)) <= max_tokens:
                return truncated, True
    except (ImportError, OSError):
        # Match token_count's offline fallback with deterministic word-boundary
        # prefixes. Descending evaluation preserves the same no-monotonicity
        # assumption as the tokenizer path.
        word_ends = [match.end() for match in re.finditer(r"\S+", full_text)]
        for word_count in range(min(len(word_ends), max_tokens), 0, -1):
            truncated = candidate(full_text[: word_ends[word_count - 1]])
            if token_count(str(truncated)) <= max_tokens:
                return truncated, True

    # A notice without any source characters is not useful source context.
    # Omit it so callers can report ``omitted_budget`` honestly.
    return None, True


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
    """Assemble a single source's full text plus its insights.

    Used by the source-chat graph. If ``max_tokens`` is given, the source text
    is kept in full when it fits, then insights are retained in fetch order
    while space remains. When the source alone exceeds the budget, a bounded
    share is reserved for insights and the source is explicitly truncated into
    the remaining space instead of being dropped.

    Returns a dict with "sources", "notes" (always empty), "insights",
    "total_tokens", "total_items" and per-type counts in "metadata".
    """
    try:
        sources: list = []
        insights: list = []
        source_truncated = False
        source_text_status = "not_found"

        try:
            full_source_id = _ensure_prefix("source", source_id)
            source = await Source.get(full_source_id)
        except NotFoundError:
            source = None

        if source:
            insight_objects = await source.get_insights()
            source_context = await source.get_context(
                context_size="long",
                insights=insight_objects,
            )
            # Insights have their own budgeted items below. Keeping the nested
            # copy would double-count them while the formatter ignores it.
            source_context = {**source_context, "insights": []}
            budgeted_source: Optional[Dict[str, Any]] = source_context

            insight_items = []
            for insight in insight_objects:
                insight_content = {
                    "id": insight.id,
                    "source_id": source.id,
                    "insight_type": insight.insight_type,
                    "content": insight.content,
                }
                insight_items.append(
                    (insight_content, token_count(str(insight_content)))
                )

            source_tokens = token_count(str(source_context))
            selected_insight_tokens = 0

            if max_tokens is not None and source_tokens > max_tokens:
                # Large documents would otherwise consume the entire budget and
                # silently remove every insight. Reserve a bounded share for
                # insights, then give all unused space back to the source text.
                insight_budget = int(max_tokens * SOURCE_INSIGHT_BUDGET_RATIO)
                for insight_content, insight_tokens in insight_items:
                    if selected_insight_tokens + insight_tokens > insight_budget:
                        continue
                    insights.append(insight_content)
                    selected_insight_tokens += insight_tokens

                source_budget = max_tokens - selected_insight_tokens
                budgeted_source, source_truncated = _truncate_source_to_token_budget(
                    source_context,
                    source_budget,
                )
                source_tokens = (
                    token_count(str(budgeted_source))
                    if budgeted_source is not None
                    else 0
                )
            else:
                total_tokens = source_tokens
                for insight_content, insight_tokens in insight_items:
                    if (
                        max_tokens is not None
                        and total_tokens + insight_tokens > max_tokens
                    ):
                        continue
                    insights.append(insight_content)
                    selected_insight_tokens += insight_tokens
                    total_tokens += insight_tokens

            if budgeted_source is None:
                source_text_status = "omitted_budget"
            else:
                full_text = budgeted_source.get("full_text")
                if isinstance(full_text, str) and full_text.strip():
                    source_text_status = (
                        "truncated" if source_truncated else "available"
                    )
                else:
                    source_text_status = "missing"

            if budgeted_source is not None:
                sources.append(budgeted_source)
            total_tokens = source_tokens + selected_insight_tokens
        else:
            logger.warning(f"Source {source_id} not found")
            total_tokens = 0

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
                "source_text_status": source_text_status,
                "source_truncated": source_truncated,
            },
        }
    except Exception as e:
        logger.error(f"Error building context: {str(e)}")
        raise DatabaseOperationError(f"Failed to build context: {str(e)}")
