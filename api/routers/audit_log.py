from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import CurrentUser, require_admin
from api.models import AuditLogListResponse, AuditLogResponse
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


def _audit_log_response(row: dict) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(row.get("id", "")),
        actor_id=str(row.get("actor_id", "")) if row.get("actor_id") else None,
        actor_username=row.get("actor_username"),
        action=row.get("action", ""),
        target_type=row.get("target_type"),
        target_id=row.get("target_id"),
        metadata=row.get("metadata") or {},
        ip_address=row.get("ip_address"),
        user_agent=row.get("user_agent"),
        created=str(row.get("created", "")),
    )


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_admin),
):
    rows = await AuditLogRepository.list_logs(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )
    total = await AuditLogRepository.count_logs(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
    )
    return AuditLogListResponse(
        items=[_audit_log_response(row) for row in rows],
        limit=limit,
        offset=offset,
        total=total,
    )
