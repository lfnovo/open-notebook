from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query


class WorkspaceRepository:
    """Named workspace queries used by workspace services."""

    @staticmethod
    async def get_workspace(workspace_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM $workspace_id",
            {"workspace_id": ensure_record_id(workspace_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def get_personal_workspace(user_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM workspace
            WHERE type = 'personal' AND owner_id = $user_id
            LIMIT 1
            """,
            {"user_id": ensure_record_id(user_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def ensure_personal_workspace(
        *,
        user_id: str,
        display_name: Optional[str] = None,
    ) -> dict[str, Any]:
        existing = await WorkspaceRepository.get_personal_workspace(user_id)
        if existing:
            return existing

        result = await repo_query(
            """
            CREATE workspace SET
                name = $name,
                type = 'personal',
                owner_id = $user_id,
                team_id = NONE,
                created_by = $user_id,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                "name": display_name or "Personal Workspace",
                "user_id": ensure_record_id(user_id),
            },
        )
        return result[0] if result else {}

    @staticmethod
    async def get_team_workspace(team_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM workspace
            WHERE type = 'team' AND team_id = $team_id
            LIMIT 1
            """,
            {"team_id": ensure_record_id(team_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def ensure_team_workspace(
        *,
        team_id: str,
        name: str,
        created_by: Optional[str] = None,
    ) -> dict[str, Any]:
        existing = await WorkspaceRepository.get_team_workspace(team_id)
        if existing:
            return existing

        result = await repo_query(
            """
            CREATE workspace SET
                name = $name,
                type = 'team',
                owner_id = NONE,
                team_id = $team_id,
                created_by = $created_by,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                "name": name,
                "team_id": ensure_record_id(team_id),
                "created_by": ensure_record_id(created_by) if created_by else None,
            },
        )
        return result[0] if result else {}

    @staticmethod
    async def list_for_user(
        *,
        user_id: str,
        include_all_for_admin: bool,
    ) -> list[dict[str, Any]]:
        if include_all_for_admin:
            return await repo_query(
                """
                SELECT *,
                    IF type = 'personal' THEN 'owner' ELSE NONE END AS current_user_role,
                    true AS can_manage
                FROM workspace
                ORDER BY type ASC, name ASC
                """
            )

        return await repo_query(
            """
            SELECT *,
                IF type = 'personal' THEN 'owner'
                ELSE (SELECT VALUE role FROM team_member
                    WHERE team = $parent.team_id AND user = $user_id AND status = 'active'
                    LIMIT 1)[0]
                END AS current_user_role,
                IF type = 'personal' THEN true
                ELSE (SELECT VALUE role FROM team_member
                    WHERE team = $parent.team_id AND user = $user_id AND status = 'active'
                    LIMIT 1)[0] IN ['owner', 'admin']
                END AS can_manage
            FROM workspace
            WHERE owner_id = $user_id
                OR team_id IN (
                    SELECT VALUE team FROM team_member
                    WHERE user = $user_id AND status = 'active'
                )
            ORDER BY type ASC, name ASC
            """,
            {"user_id": ensure_record_id(user_id)},
        )

    @staticmethod
    async def user_can_access(
        *,
        workspace_id: str,
        user_id: str,
        include_all_for_admin: bool,
    ) -> bool:
        if include_all_for_admin:
            return True
        result = await repo_query(
            """
            SELECT id
            FROM workspace
            WHERE id = $workspace_id
                AND (
                    owner_id = $user_id
                    OR team_id IN (
                        SELECT VALUE team FROM team_member
                        WHERE user = $user_id AND status = 'active'
                    )
                )
            LIMIT 1
            """,
            {
                "workspace_id": ensure_record_id(workspace_id),
                "user_id": ensure_record_id(user_id),
            },
        )
        return bool(result)

    @staticmethod
    async def current_user_role(
        *,
        workspace_id: str,
        user_id: str,
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT
                type,
                owner_id,
                team_id,
                IF type = 'personal' AND owner_id = $user_id THEN 'owner'
                ELSE (SELECT VALUE role FROM team_member
                    WHERE team = $parent.team_id AND user = $user_id AND status = 'active'
                    LIMIT 1)[0]
                END AS current_user_role
            FROM $workspace_id
            LIMIT 1
            """,
            {
                "workspace_id": ensure_record_id(workspace_id),
                "user_id": ensure_record_id(user_id),
            },
        )
        return result[0] if result else None
