from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_delete, repo_query


PUBLIC_TEAM_ID = "team:public"


class ShareRepository:
    """Named share_grant queries."""

    @staticmethod
    async def list_resource_grants(
        *, resource_type: str, resource_id: str
    ) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT * FROM share_grant
            WHERE resource_type = $resource_type AND resource_id = $resource_id
            ORDER BY created DESC
            """,
            {"resource_type": resource_type, "resource_id": resource_id},
        )

    @staticmethod
    async def get_grant(grant_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM $grant_id",
            {"grant_id": ensure_record_id(grant_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def find_grant(
        *,
        resource_type: str,
        resource_id: str,
        target_type: str,
        target_id: str,
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT * FROM share_grant
            WHERE resource_type = $resource_type
              AND resource_id = $resource_id
              AND target_type = $target_type
              AND target_id = $target_id
            LIMIT 1
            """,
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "target_type": target_type,
                "target_id": target_id,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def create_grant(
        *,
        resource_type: str,
        resource_id: str,
        target_type: str,
        target_id: str,
        permission: str,
        created_by: Optional[str],
    ) -> Optional[dict[str, Any]]:
        existing = await ShareRepository.find_grant(
            resource_type=resource_type,
            resource_id=resource_id,
            target_type=target_type,
            target_id=target_id,
        )
        if existing:
            return existing

        result = await repo_query(
            """
            CREATE share_grant SET
                resource_type = $resource_type,
                resource_id = $resource_id,
                target_type = $target_type,
                target_id = $target_id,
                permission = $permission,
                created_by = $created_by,
                created = time::now()
            RETURN AFTER
            """,
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "target_type": target_type,
                "target_id": target_id,
                "permission": permission,
                "created_by": ensure_record_id(created_by) if created_by else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def delete_grant(grant_id: str) -> None:
        await repo_delete(grant_id)

    @staticmethod
    async def public_grant(resource_type: str, resource_id: str) -> Optional[dict[str, Any]]:
        return await ShareRepository.find_grant(
            resource_type=resource_type,
            resource_id=resource_id,
            target_type="team",
            target_id=PUBLIC_TEAM_ID,
        )

    @staticmethod
    async def has_read_grant(
        *,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str],
        team_ids: list[str],
    ) -> bool:
        target_conditions = [
            "(target_type = 'team' AND target_id = $public_team_id)",
        ]
        params: dict[str, Any] = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "public_team_id": PUBLIC_TEAM_ID,
            "team_ids": team_ids,
        }
        if user_id:
            target_conditions.append("(target_type = 'user' AND target_id = $user_id)")
            params["user_id"] = str(user_id)
        if team_ids:
            target_conditions.append("(target_type = 'team' AND target_id IN $team_ids)")

        result = await repo_query(
            f"""
            SELECT count() AS count FROM share_grant
            WHERE resource_type = $resource_type
              AND resource_id = $resource_id
              AND permission IN ['read', 'write', 'owner']
              AND ({' OR '.join(target_conditions)})
            GROUP ALL
            """,
            params,
        )
        return bool(result and result[0].get("count", 0) > 0)

    @staticmethod
    async def referencing_notebook_owner_ids(resource_type: str, resource_id: str) -> list[str]:
        if resource_type == "source":
            result = await repo_query(
                """
                SELECT out FROM reference WHERE in = $source_id FETCH out
                """,
                {"source_id": ensure_record_id(resource_id)},
            )
        else:
            result = []
        owner_ids: set[str] = set()
        for row in result or []:
            notebook = row.get("out") if isinstance(row, dict) else None
            if isinstance(notebook, dict) and notebook.get("owner_id"):
                owner_ids.add(str(notebook["owner_id"]))
        return sorted(owner_ids)
