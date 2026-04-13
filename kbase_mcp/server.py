"""
MCP server exposing knowledge-base tools via FastMCP.

Tools authenticate callers with MCP API keys and delegate to
GraphService and vector_search for actual retrieval.

When the ``mcp`` library (PyPI) is not installed the module still
loads — tool functions remain usable as plain async functions for
tests, and the FastMCP registration is skipped.
"""

from loguru import logger

_HAS_FASTMCP = False
_FastMCP = None

try:
    from mcp.server.fastmcp import FastMCP

    _FastMCP = FastMCP
    _HAS_FASTMCP = True
except (ImportError, ModuleNotFoundError):
    pass

if not _HAS_FASTMCP:
    logger.warning(
        "mcp package (PyPI) is not installed. MCP server tools will be "
        "unavailable. Install with: pip install 'mcp>=1.0.0'"
    )

from kbase_mcp.auth import validate_api_key  # noqa: E402

# Lazy imports — resolved at call time when a running app context exists.
from open_notebook.domain.notebook import vector_search  # noqa: E402
from open_notebook.domain.workspace import Workspace  # noqa: E402
from open_notebook.services.graph_service import GraphService  # noqa: E402

if _HAS_FASTMCP and _FastMCP is not None:
    mcp_server = _FastMCP("kbase")
else:
    mcp_server = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Database initialization flag
# ---------------------------------------------------------------------------

_db_initialized = False


async def _ensure_db() -> None:
    """Initialize the SurrealDB connection once on first tool call."""
    global _db_initialized
    if _db_initialized:
        return

    from open_notebook.database.repository import db_connection

    # Verify connectivity by opening and closing a connection
    async with db_connection():
        pass

    _db_initialized = True
    logger.info("MCP server: SurrealDB connection verified")


# ---------------------------------------------------------------------------
# Tool: search_kb
# ---------------------------------------------------------------------------


async def search_kb(
    query: str,
    workspace_ids: list[str],
    api_key: str,
) -> list[dict] | dict:
    """Search one or more workspaces. Returns ranked results with content and source."""
    try:
        await _ensure_db()
        key_record = await validate_api_key(api_key)

        # Scope check
        for ws_id in workspace_ids:
            if ws_id not in key_record.workspace_ids:
                raise ValueError(f"Workspace {ws_id} is not in the API key scope")

        all_results: list[dict] = []

        for ws_id in workspace_ids:
            # Graph-based search
            try:
                graph_result = await GraphService.query(ws_id, query)
                if graph_result:
                    all_results.append(
                        {
                            "content": graph_result,
                            "source_name": "knowledge_graph",
                            "confidence": 0.9,
                            "workspace_id": ws_id,
                            "type": "graph",
                        }
                    )
            except Exception as error:
                logger.warning(f"Graph query failed for {ws_id}: {error}")

            # Vector search
            try:
                vec_results = await vector_search(
                    keyword=query,
                    results=10,
                    source=True,
                    note=True,
                    workspace_id=ws_id,
                )
                for item in vec_results:
                    all_results.append(
                        {
                            "content": item.get("content", ""),
                            "source_name": item.get(
                                "title", item.get("source_name", "")
                            ),
                            "confidence": item.get("score", 0.5),
                            "workspace_id": ws_id,
                            "type": "vector",
                        }
                    )
            except Exception as error:
                logger.warning(f"Vector search failed for {ws_id}: {error}")

        # Deduplicate by content, keep highest confidence
        seen: dict[str, dict] = {}
        for r in all_results:
            key = r["content"]
            if key not in seen or r["confidence"] > seen[key]["confidence"]:
                seen[key] = r

        return sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Tool error in search_kb: {e}")
        return {"error": "Internal error processing request"}


# ---------------------------------------------------------------------------
# Tool: list_workspaces
# ---------------------------------------------------------------------------


async def list_workspaces(api_key: str) -> list[dict] | dict:
    """List workspaces accessible to the authenticated user."""
    try:
        await _ensure_db()
        key_record = await validate_api_key(api_key)

        results: list[dict] = []
        for ws_id in key_record.workspace_ids:
            try:
                workspace = await Workspace.get(ws_id)
                results.append(
                    {
                        "id": str(workspace.id),
                        "name": workspace.name,
                        "description": workspace.description,
                        "visibility": workspace.visibility,
                    }
                )
            except Exception as error:
                logger.warning(f"Could not load workspace {ws_id}: {error}")

        return results
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Tool error in list_workspaces: {e}")
        return {"error": "Internal error processing request"}


# ---------------------------------------------------------------------------
# Tool: get_entity
# ---------------------------------------------------------------------------


async def get_entity(
    name: str,
    workspace_id: str,
    api_key: str,
) -> dict:
    """Get a knowledge graph entity by name."""
    try:
        await _ensure_db()
        key_record = await validate_api_key(api_key)

        if workspace_id not in key_record.workspace_ids:
            raise ValueError(f"Workspace {workspace_id} is not in the API key scope")

        entity_query = f"Tell me everything about the entity: {name}"
        graph_result = await GraphService.query(workspace_id, entity_query)

        return {
            "entity_name": name,
            "workspace_id": workspace_id,
            "description": graph_result or "",
        }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Tool error in get_entity: {e}")
        return {"error": "Internal error processing request"}


# ---------------------------------------------------------------------------
# Register tools with FastMCP when available
# ---------------------------------------------------------------------------

if _HAS_FASTMCP and mcp_server is not None:
    mcp_server.tool()(search_kb)
    mcp_server.tool()(list_workspaces)
    mcp_server.tool()(get_entity)


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------


def run_server() -> None:
    """Start the MCP server with the configured transport."""
    if not _HAS_FASTMCP or mcp_server is None:
        raise RuntimeError(
            "Cannot start MCP server: the 'mcp' package is not installed."
        )

    from kbase_mcp.config import MCP_TRANSPORT

    if MCP_TRANSPORT == "sse":
        from kbase_mcp.config import MCP_HOST, MCP_PORT

        mcp_server.run(transport="sse", host=MCP_HOST, port=MCP_PORT)
    else:
        mcp_server.run(transport="stdio")
