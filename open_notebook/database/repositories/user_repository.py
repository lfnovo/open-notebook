from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query, repo_update


class UserRepository:
    """Named app_user queries."""

    @staticmethod
    async def list_users(
        *,
        q: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if q:
            conditions.append(
                "(string::contains(string::lowercase(username), string::lowercase($q)) "
                "OR string::contains(string::lowercase(display_name ?? ''), string::lowercase($q)) "
                "OR string::contains(string::lowercase(email ?? ''), string::lowercase($q)))"
            )
            params["q"] = q
        if role:
            conditions.append("role = $role")
            params["role"] = role
        if status:
            conditions.append("status = $status")
            params["status"] = status

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return await repo_query(
            f"""
            SELECT *,
                (SELECT VALUE count() FROM source WHERE owner_id = $parent.id GROUP ALL)[0] OR 0 AS source_count,
                (SELECT VALUE count() FROM notebook WHERE owner_id = $parent.id GROUP ALL)[0] OR 0 AS notebook_count
            FROM app_user
            {where_clause}
            ORDER BY created DESC
            LIMIT $limit START $offset
            """,
            params,
        )

    @staticmethod
    async def count_users(
        *,
        q: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        conditions = []
        params: dict[str, Any] = {}
        if q:
            conditions.append(
                "(string::contains(string::lowercase(username), string::lowercase($q)) "
                "OR string::contains(string::lowercase(display_name ?? ''), string::lowercase($q)) "
                "OR string::contains(string::lowercase(email ?? ''), string::lowercase($q)))"
            )
            params["q"] = q
        if role:
            conditions.append("role = $role")
            params["role"] = role
        if status:
            conditions.append("status = $status")
            params["status"] = status
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        result = await repo_query(
            f"SELECT count() AS count FROM app_user {where_clause} GROUP ALL",
            params,
        )
        return result[0]["count"] if result else 0

    @staticmethod
    async def get_user(user_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM $user_id",
            {"user_id": ensure_record_id(user_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM app_user WHERE username = $username LIMIT 1",
            {"username": username},
        )
        return result[0] if result else None

    @staticmethod
    async def create_user(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE app_user SET
                username = $username,
                email = $email,
                display_name = $display_name,
                role = $role,
                status = $status,
                hashed_password = $hashed_password,
                password_changed_at = time::now(),
                created_by = $created_by,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                **data,
                "created_by": ensure_record_id(data["created_by"])
                if data.get("created_by")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def update_user(user_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        return await repo_update("app_user", user_id, data)

    @staticmethod
    async def count_active_admins(self_excluding_user_id: Optional[str] = None) -> int:
        params: dict[str, Any] = {}
        condition = "role = 'admin' AND status = 'active'"
        if self_excluding_user_id:
            condition += " AND id != $excluding"
            params["excluding"] = ensure_record_id(self_excluding_user_id)
        result = await repo_query(
            f"SELECT count() AS count FROM app_user WHERE {condition} GROUP ALL",
            params,
        )
        return result[0]["count"] if result else 0

    @staticmethod
    async def resource_counts(user_id: str) -> dict[str, int]:
        result = await repo_query(
            """
            RETURN {
                source_count: (SELECT VALUE count() FROM source WHERE owner_id = $user_id GROUP ALL)[0] OR 0,
                notebook_count: (SELECT VALUE count() FROM notebook WHERE owner_id = $user_id GROUP ALL)[0] OR 0
            }
            """,
            {"user_id": ensure_record_id(user_id)},
        )
        return result[0] if result else {"source_count": 0, "notebook_count": 0}
