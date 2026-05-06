from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import (
    ensure_record_id,
    repo_query,
    repo_transaction,
    repo_update,
)


class TeamRepository:
    """Named team and team_member queries."""

    MODEL_DEFAULT_FIELDS = (
        "default_chat_model",
        "default_embedding_model",
        "default_transformation_model",
        "default_tools_model",
        "large_context_model",
    )

    @staticmethod
    async def list_teams(
        *,
        user_id: Optional[str],
        include_all_for_admin: bool,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "user_id": ensure_record_id(user_id) if user_id else None,
        }
        if not include_all_for_admin:
            conditions.append(
                "(type = 'system') OR id IN (SELECT VALUE team FROM team_member WHERE user = $user_id AND status = 'active')"
            )
        if q:
            conditions.append(
                "(string::contains(string::lowercase(name), string::lowercase($q)) "
                "OR string::contains(string::lowercase(slug), string::lowercase($q)))"
            )
            params["q"] = q
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return await repo_query(
            f"""
            SELECT *,
                (SELECT VALUE count() FROM team_member WHERE team = $parent.id AND status = 'active' GROUP ALL)[0] OR 0 AS member_count,
                (SELECT VALUE count() FROM share_grant WHERE target_type = 'team' AND target_id = type::string($parent.id) GROUP ALL)[0] OR 0 AS share_count,
                (SELECT VALUE role FROM team_member WHERE team = $parent.id AND user = $user_id AND status = 'active' LIMIT 1)[0] AS current_user_role
            FROM team
            {where_clause}
            ORDER BY type ASC, name ASC
            LIMIT $limit START $offset
            """,
            params,
        )

    @staticmethod
    async def get_team(team_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query("SELECT * FROM $team_id", {"team_id": ensure_record_id(team_id)})
        return result[0] if result else None

    @staticmethod
    async def get_team_by_slug(slug: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM team WHERE slug = $slug LIMIT 1",
            {"slug": slug},
        )
        return result[0] if result else None

    @staticmethod
    async def create_team(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE team SET
                slug = $slug,
                name = $name,
                type = 'workspace',
                created_by = $created_by,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                "slug": data["slug"],
                "name": data["name"],
                "created_by": ensure_record_id(data["created_by"])
                if data.get("created_by")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def update_team(team_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        return await repo_update("team", team_id, data)

    @staticmethod
    async def update_model_defaults(
        team_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        default_data = {
            field: ensure_record_id(value) if value else None
            for field, value in data.items()
            if field in TeamRepository.MODEL_DEFAULT_FIELDS
        }
        rows = await repo_update("team", team_id, default_data)
        return rows[0] if rows else default_data

    @staticmethod
    async def clear_invalid_model_defaults(
        team_id: str, model_ids: list[str]
    ) -> None:
        await repo_query(
            """
            UPDATE $team_id SET
                default_chat_model = IF default_chat_model IN $model_ids THEN default_chat_model ELSE NONE END,
                default_embedding_model = IF default_embedding_model IN $model_ids THEN default_embedding_model ELSE NONE END,
                default_transformation_model = IF default_transformation_model IN $model_ids THEN default_transformation_model ELSE NONE END,
                default_tools_model = IF default_tools_model IN $model_ids THEN default_tools_model ELSE NONE END,
                large_context_model = IF large_context_model IN $model_ids THEN large_context_model ELSE NONE END
            """,
            {
                "team_id": ensure_record_id(team_id),
                "model_ids": [ensure_record_id(model_id) for model_id in model_ids],
            },
        )

    @staticmethod
    async def delete_team(team_id: str) -> None:
        await repo_transaction(
            """
            DELETE team_member WHERE team = $team_id;
            DELETE team_model WHERE team = $team_id;
            DELETE team_transformation WHERE team = $team_id;
            DELETE share_grant WHERE target_type = 'team' AND target_id = $team_id_string;
            DELETE workspace WHERE team_id = $team_id;
            DELETE $team_id;
            """,
            {
                "team_id": ensure_record_id(team_id),
                "team_id_string": str(team_id),
            },
        )

    @staticmethod
    async def list_members(
        *,
        team_id: str,
        q: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions = ["team = $team_id"]
        params: dict[str, Any] = {
            "team_id": ensure_record_id(team_id),
            "limit": limit,
            "offset": offset,
        }
        if role:
            conditions.append("role = $role")
            params["role"] = role
        if status:
            conditions.append("status = $status")
            params["status"] = status
        return await repo_query(
            f"""
            SELECT *
            FROM team_member
            WHERE {' AND '.join(conditions)}
            ORDER BY role ASC, created ASC
            LIMIT $limit START $offset
            FETCH user
            """,
            params,
        )

    @staticmethod
    async def get_member(team_id: str, user_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT * FROM team_member
            WHERE team = $team_id AND user = $user_id
            LIMIT 1
            """,
            {
                "team_id": ensure_record_id(team_id),
                "user_id": ensure_record_id(user_id),
            },
        )
        return result[0] if result else None

    @staticmethod
    async def create_member(
        *, team_id: str, user_id: str, role: str, status: str = "active"
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE team_member SET
                team = $team_id,
                user = $user_id,
                role = $role,
                status = $status,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                "team_id": ensure_record_id(team_id),
                "user_id": ensure_record_id(user_id),
                "role": role,
                "status": status,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def update_member(
        *, team_id: str, user_id: str, role: str, status: str = "active"
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            UPDATE team_member SET
                role = $role,
                status = $status,
                updated = time::now()
            WHERE team = $team_id AND user = $user_id
            RETURN AFTER
            """,
            {
                "team_id": ensure_record_id(team_id),
                "user_id": ensure_record_id(user_id),
                "role": role,
                "status": status,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def remove_member(team_id: str, user_id: str) -> None:
        await repo_query(
            "DELETE team_member WHERE team = $team_id AND user = $user_id",
            {
                "team_id": ensure_record_id(team_id),
                "user_id": ensure_record_id(user_id),
            },
        )

    @staticmethod
    async def count_active_owners(
        team_id: str, *, excluding_user_id: Optional[str] = None
    ) -> int:
        params: dict[str, Any] = {"team_id": ensure_record_id(team_id)}
        condition = "team = $team_id AND role = 'owner' AND status = 'active'"
        if excluding_user_id:
            condition += " AND user != $excluding"
            params["excluding"] = ensure_record_id(excluding_user_id)
        result = await repo_query(
            f"SELECT count() AS count FROM team_member WHERE {condition} GROUP ALL",
            params,
        )
        return result[0]["count"] if result else 0

    @staticmethod
    async def user_team_ids(user_id: str) -> list[str]:
        result = await repo_query(
            "SELECT VALUE type::string(team) FROM team_member WHERE user = $user_id AND status = 'active'",
            {"user_id": ensure_record_id(user_id)},
        )
        return [str(item) for item in result or []]

    @staticmethod
    async def dependency_counts(team_id: str) -> dict[str, int]:
        result = await repo_query(
            """
            RETURN {
                active_members: (SELECT VALUE count() FROM team_member WHERE team = $team_id AND status = 'active' GROUP ALL)[0] OR 0,
                share_grants: (SELECT VALUE count() FROM share_grant WHERE target_type = 'team' AND target_id = $team_id_string GROUP ALL)[0] OR 0
            }
            """,
            {
                "team_id": ensure_record_id(team_id),
                "team_id_string": str(team_id),
            },
        )
        if isinstance(result, dict):
            return result
        return result[0] if result else {"active_members": 0, "share_grants": 0}
