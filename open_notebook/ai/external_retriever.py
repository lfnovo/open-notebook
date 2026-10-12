"""Optional external MCP retriever for Ask.

When ``OPEN_NOTEBOOK_EXTERNAL_MCP_URL`` is set, Ask also calls one tool on a
Streamable HTTP MCP server and mixes those snippets with local vector hits.

The connector is an opaque context source. This module does not rank, filter,
or interpret its results beyond shaping them into the dicts Ask already puts
in the prompt. It is off unless the URL is set, and any failure returns no
rows so a down connector cannot break local Ask.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_TOOL = "search"


def _config() -> dict[str, Any] | None:
    url = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", "").strip()
    if not url:
        return None
    tool = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_SEARCH_TOOL", "").strip()
    return {
        "url": url,
        "token": os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN", "").strip() or None,
        "tool": tool or _DEFAULT_TOOL,
        "timeout": _timeout_seconds(),
    }


def _timeout_seconds() -> float:
    raw = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    if value <= 0:
        return _DEFAULT_TIMEOUT_SECONDS
    return value


def _external_id(raw: Any, index: int) -> str:
    """Keep connector ids from colliding with notebook record ids.

    Local citations look like ``source:…``, ``note:…`` or ``insight:…``.
    External snippets are not those records, so every id is namespaced.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        return f"external:{index}"
    if text.startswith("external:"):
        return text
    return f"external:{text}"


def _row(item: dict[str, Any], index: int) -> dict[str, Any] | None:
    content = item.get("content")
    if not isinstance(content, str) or not content.strip():
        content = item.get("text")
    if not isinstance(content, str) or not content.strip():
        return None
    row: dict[str, Any] = {
        "id": _external_id(item.get("id"), index),
        "content": content.strip(),
    }
    score = item.get("score", item.get("similarity"))
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        row["similarity"] = float(score)
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        row["title"] = title.strip()
    return row


def rows_from_tool_result(result: Any) -> list[dict[str, Any]]:
    """Turn one MCP ``tools/call`` result into Ask result dicts."""
    if getattr(result, "isError", False):
        return []

    structured = getattr(result, "structuredContent", None)
    candidates: list[Any] | None = None
    if isinstance(structured, dict):
        for key in ("results", "items", "documents"):
            value = structured.get(key)
            if isinstance(value, list):
                candidates = value
                break
        if candidates is None and (
            isinstance(structured.get("content"), str)
            or isinstance(structured.get("text"), str)
        ):
            candidates = [structured]

    rows: list[dict[str, Any]] = []
    if candidates is not None:
        for item in candidates:
            if not isinstance(item, dict):
                continue
            row = _row(item, len(rows) + 1)
            if row is not None:
                rows.append(row)
        return rows

    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    if not parts:
        return []
    row = _row({"content": "\n\n".join(parts)}, 1)
    return [row] if row is not None else []


async def _call_search_tool(
    url: str,
    token: str | None,
    tool: str,
    query: str,
    limit: int,
    timeout: float,
) -> Any:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with streamablehttp_client(url, headers=headers, timeout=timeout) as (
        read,
        write,
        _session_id,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(tool, {"query": query, "limit": limit})


async def external_mcp_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the configured MCP connector, or return no rows.

    The tool is called with ``{"query": query, "limit": limit}``. Connectors
    that use different argument names are not mapped here.
    """
    cfg = _config()
    if cfg is None or not query.strip():
        return []
    try:
        result = await _call_search_tool(
            cfg["url"],
            cfg["token"],
            cfg["tool"],
            query,
            limit,
            cfg["timeout"],
        )
    except Exception as exc:
        logger.warning("External MCP retriever failed: {}", exc)
        return []
    if getattr(result, "isError", False):
        logger.warning("External MCP tool {!r} returned an error", cfg["tool"])
        return []
    return rows_from_tool_result(result)
