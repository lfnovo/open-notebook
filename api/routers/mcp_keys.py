"""
MCP API key management endpoints.

Provides create, list, and revoke operations for MCP API keys.
All endpoints require Clerk authentication.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.mcp_keys_service import generate_api_key, list_api_keys, revoke_api_key
from api.models import CreateMcpKeyRequest, McpKeyListResponse, McpKeyResponse
from api.rbac import require_viewer

router = APIRouter()


@router.post("/mcp-keys", response_model=McpKeyResponse, status_code=201)
async def create_mcp_key_endpoint(body: CreateMcpKeyRequest, request: Request):
    """Generate a new MCP API key. Requires Clerk auth."""
    user_id: str = request.state.user_id

    # Verify the user has at least viewer role on each requested workspace
    for ws_id in body.workspace_ids:
        await require_viewer(ws_id, request)

    expires_in_days = body.expires_in_days

    try:
        result = await generate_api_key(
            user_id=user_id,
            workspace_ids=body.workspace_ids,
            label=body.label,
            expires_in_days=expires_in_days,
        )
        return McpKeyResponse(**result)
    except Exception as error:
        logger.error(f"Error creating MCP key: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/mcp-keys", response_model=McpKeyListResponse)
async def list_mcp_keys_endpoint(request: Request):
    """List the authenticated user's MCP API keys."""
    user_id: str = request.state.user_id

    try:
        keys = await list_api_keys(user_id)
        return McpKeyListResponse(keys=[McpKeyResponse(**k) for k in keys])
    except Exception as error:
        logger.error(f"Error listing MCP keys: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/mcp-keys/{key_id}")
async def revoke_mcp_key_endpoint(key_id: str, request: Request):
    """Revoke an MCP API key. Requires Clerk auth."""
    user_id: str = request.state.user_id

    try:
        await revoke_api_key(key_id, user_id)
        return {"message": "API key revoked successfully"}
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error))
    except Exception as error:
        logger.error(f"Error revoking MCP key {key_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")
