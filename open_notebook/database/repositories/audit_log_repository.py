from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query


class AuditLogRepository:
    """Named audit-log queries."""

    @staticmethod
    def _filter_clause(
        *,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> tuple[str, dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {}
        if actor_id:
            conditions.append("actor_id = $actor_id")
            params["actor_id"] = ensure_record_id(actor_id)
        if action:
            conditions.append("action = $action")
            params["action"] = action
        if target_id:
            conditions.append("target_id = $target_id")
            params["target_id"] = target_id

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return where_clause, params

    @staticmethod
    async def create(
        *,
        action: str,
        actor_id: Optional[str] = None,
        actor_username: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict[str, Any] | None:
        result = await repo_query(
            """
            CREATE audit_log SET
                actor_id = $actor_id,
                actor_username = $actor_username,
                action = $action,
                target_type = $target_type,
                target_id = $target_id,
                metadata = $metadata,
                ip_address = $ip_address,
                user_agent = $user_agent,
                created = time::now()
            RETURN AFTER
            """,
            {
                "actor_id": ensure_record_id(actor_id) if actor_id else None,
                "actor_username": actor_username,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "metadata": metadata or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def list_logs(
        *,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where_clause, params = AuditLogRepository._filter_clause(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
        )
        params.update({"limit": limit, "offset": offset})
        return await repo_query(
            f"""
            SELECT * FROM audit_log
            {where_clause}
            ORDER BY created DESC
            LIMIT $limit START $offset
            """,
            params,
        )

    @staticmethod
    async def count_logs(
        *,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> int:
        where_clause, params = AuditLogRepository._filter_clause(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
        )
        result = await repo_query(
            f"""
            SELECT count() AS count FROM audit_log
            {where_clause}
            GROUP ALL
            """,
            params,
        )
        return int(result[0].get("count", 0)) if result else 0
