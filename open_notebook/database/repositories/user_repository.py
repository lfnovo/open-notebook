from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query, repo_update


class UserRepository:
    """Named app_user queries."""

    @staticmethod
    def _matches_status(row: dict[str, Any], status: Optional[str]) -> bool:
        if not status:
            return True
        return row.get("status", "active") == status

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
        paginate_in_query = status is None
        if paginate_in_query:
            params["limit"] = limit
            params["offset"] = offset

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = "LIMIT $limit START $offset" if paginate_in_query else ""
        rows = await repo_query(
            f"""
            SELECT *,
                (SELECT VALUE count() FROM source WHERE owner_id = $parent.id GROUP ALL)[0] OR 0 AS source_count,
                (SELECT VALUE count() FROM notebook WHERE owner_id = $parent.id GROUP ALL)[0] OR 0 AS notebook_count
            FROM app_user
            {where_clause}
            ORDER BY created DESC
            {limit_clause}
            """,
            params,
        )
        if status:
            filtered = [row for row in rows if UserRepository._matches_status(row, status)]
            return filtered[offset : offset + limit]
        return rows

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
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        if status:
            rows = await repo_query(f"SELECT * FROM app_user {where_clause}", params)
            return sum(1 for row in rows if UserRepository._matches_status(row, status))
        result = await repo_query(
            f"SELECT count() AS count FROM app_user {where_clause} GROUP ALL", params
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
    async def get_user_by_wechat_identity(
        *, unionid: Optional[str], openid: str
    ) -> Optional[dict[str, Any]]:
        conditions = ["wechat_openid = $openid"]
        params: dict[str, Any] = {"openid": openid}
        if unionid:
            conditions.insert(0, "wechat_unionid = $unionid")
            params["unionid"] = unionid
        result = await repo_query(
            f"""
            SELECT * FROM app_user
            WHERE {" OR ".join(conditions)}
            LIMIT 1
            """,
            params,
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
    async def create_wechat_user(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE app_user SET
                username = $username,
                email = NONE,
                display_name = $display_name,
                avatar_url = $avatar_url,
                login_provider = 'wechat',
                wechat_openid = $wechat_openid,
                wechat_unionid = $wechat_unionid,
                role = 'user',
                status = 'active',
                hashed_password = $hashed_password,
                password_changed_at = time::now(),
                last_login_at = time::now(),
                created_by = NONE,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {**data, "hashed_password": data.get("hashed_password", "")},
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
