"""Generic external MCP retriever for Ask / source-chat context.

When OPEN_NOTEBOOK_EXTERNAL_MCP_URL is set, Ask (and optionally other
retrieval paths) can augment local vector search with results from any
MCP server that exposes a search-style tool.

This module is deliberately free of any vendor- or product-specific logic.
The external server is responsible for ranking, freshness, access control, etc.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

import httpx

from open_notebook.exceptions import ExternalServiceError


def _get_config() -> Optional[dict]:
    url = os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_URL", "").strip()
    if not url:
        return None
    return {
        "url": url.rstrip("/"),
        "token": os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN", "").strip() or None,
        "tool": os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_SEARCH_TOOL", "search").strip() or "search",
        "timeout": float(os.environ.get("OPEN_NOTEBOOK_EXTERNAL_MCP_TIMEOUT", "15")),
    }


async def external_mcp_search(query: str, limit: int = 5) -> List[dict[str, Any]]:
    """Call the configured external MCP search tool.

    Returns a list of result dicts. Expected (but not strictly required) shape
    from the MCP tool:
        {"content": str, "id": str | None, "score": float | None, "metadata": dict | None}

    If the external server is unreachable or returns an error, an
    ExternalServiceError is raised so the caller can decide whether to fail
    open or closed.
    """
    cfg = _get_config()
    if not cfg:
        return []

    headers = {"Content-Type": "application/json"}
    if cfg["token"]:
        headers["Authorization"] = f"Bearer {cfg['token']}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": cfg["tool"],
            "arguments": {"query": query, "limit": limit},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            resp = await client.post(f"{cfg['url']}/mcp", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise ExternalServiceError(f"External MCP retriever failed: {e}") from e

    if "error" in data:
        raise ExternalServiceError(f"External MCP tool error: {data['error']}")

    result = data.get("result", {})
    # MCP tools/call result is usually {"content": [{"type": "text", "text": "..."}], ...}
    # or a direct structured content. We normalise to a list of dicts.
    content = result.get("content") or result.get("contents") or []
    if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
        # Simple text content — wrap as one result
        text = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
        return [{"content": text, "id": None, "score": None, "source": "external_mcp"}]

    # Assume the tool already returned a list of structured results
    if isinstance(result.get("results"), list):
        return result["results"]
    if isinstance(content, list):
        return content
    return []
