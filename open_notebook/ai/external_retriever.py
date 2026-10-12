"""Optional external MCP retriever for Ask.

When ``OPEN_NOTEBOOK_EXTERNAL_MCP_URL`` is set, Ask also calls one tool on a
Streamable HTTP MCP server and mixes those snippets with local vector hits.

The connector is an opaque context source. This module does not rank, filter,
or interpret its results beyond shaping them into the dicts Ask already puts
in the prompt. The tool name, the name of its limit argument, and where the
token comes from are configuration. It is off unless the URL is set, and any
failure returns no rows so a down connector cannot break local Ask.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger

_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_TOOL = "search"
_DEFAULT_LIMIT = 5
_DEFAULT_LIMIT_ARG = "limit"
_LIST_KEYS = ("results", "items", "documents")


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _limit_arg() -> str:
    raw = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_LIMIT_ARG", "").strip()
    if not raw or not raw.isidentifier() or raw == "query":
        return _DEFAULT_LIMIT_ARG
    return raw


def _token() -> str | None:
    inline = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN", "").strip()
    if inline:
        return inline
    path = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN_FILE", "").strip()
    if not path:
        return None
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("External MCP token file is unreadable: {}", exc)
        return None
    return value or None


def _config() -> dict[str, Any] | None:
    url = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", "").strip()
    if not url:
        return None
    tool = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_SEARCH_TOOL", "").strip()
    return {
        "url": url,
        "token": _token(),
        "tool": tool or _DEFAULT_TOOL,
        "timeout": _timeout_seconds(),
        "limit": _positive_int("OPEN_NOTEBOOK_EXTERNAL_MCP_LIMIT", _DEFAULT_LIMIT),
        "limit_arg": _limit_arg(),
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
    if isinstance(raw, bool) or raw is None:
        text = ""
    elif isinstance(raw, int):
        text = str(raw)
    elif isinstance(raw, float) and raw.is_integer():
        text = str(int(raw))
    elif isinstance(raw, str):
        text = raw.strip()
    else:
        text = ""
    if not text:
        return f"external:{index}"
    if text.startswith("external:"):
        return text
    return f"external:{text}"


def _similarity(item: dict[str, Any]) -> float | None:
    for key in ("score", "similarity", "relevance_score", "confidence"):
        value = item.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                continue
    return None


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
    score = _similarity(item)
    if score is not None:
        row["similarity"] = score
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        row["title"] = title.strip()
    return row


def _rows_from_mappings(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = _row(item, len(rows) + 1)
        if row is not None:
            rows.append(row)
    return rows


def _rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return rows when the object is a known result envelope, else None."""
    for key in _LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return _rows_from_mappings(value)
    if isinstance(payload.get("content"), str) or isinstance(payload.get("text"), str):
        row = _row(payload, 1)
        return [row] if row is not None else []
    return None


def _rows_from_text(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if stripped[:1] in "{[":
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            rows = _rows_from_payload(parsed)
            if rows is not None:
                return rows
        elif isinstance(parsed, list):
            return _rows_from_mappings(parsed)
    row = _row({"content": text}, 1)
    return [row] if row is not None else []


def rows_from_tool_result(result: Any) -> list[dict[str, Any]]:
    """Turn one MCP ``tools/call`` result into Ask result dicts."""
    if getattr(result, "isError", False):
        return []

    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        rows = _rows_from_payload(structured)
        if rows is not None:
            return rows

    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    if not parts:
        return []
    if len(parts) == 1:
        return _rows_from_text(parts[0])
    return _rows_from_text("\n\n".join(parts))


async def _call_search_tool(
    url: str,
    token: str | None,
    tool: str,
    arguments: dict[str, Any],
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
            return await session.call_tool(tool, arguments)


async def external_mcp_search(
    query: str, limit: int | None = None
) -> list[dict[str, Any]]:
    """Search the configured MCP connector, or return no rows.

    The tool is called with ``{"query": query, "<limit argument>": limit}``.
    The limit argument name defaults to ``limit``. Connectors that use a
    different name set ``OPEN_NOTEBOOK_EXTERNAL_MCP_LIMIT_ARG``.
    """
    cfg = _config()
    if cfg is None or not query.strip():
        return []
    if limit is None:
        limit = cfg["limit"]
    arguments = {"query": query, cfg["limit_arg"]: limit}
    try:
        result = await _call_search_tool(
            cfg["url"],
            cfg["token"],
            cfg["tool"],
            arguments,
            cfg["timeout"],
        )
    except Exception as exc:
        logger.warning("External MCP retriever failed: {}", exc)
        return []
    if getattr(result, "isError", False):
        logger.warning("External MCP tool {!r} returned an error", cfg["tool"])
        return []
    return rows_from_tool_result(result)
