from __future__ import annotations

from typing import Any, Optional

from open_notebook.database.repository import ensure_record_id, repo_query

POLICY_FIELDS = (
    "member_can_read",
    "member_can_create_source",
    "member_can_update_own_source",
    "member_can_process_own_source",
    "member_can_delete_own_source",
    "member_can_remove_source",
    "member_can_create_note",
    "member_can_update_own_note",
    "member_can_delete_own_note",
    "member_can_delete_chat",
    "member_can_update_notebook",
)

DEFAULT_POLICY = {
    "member_can_read": True,
    "member_can_create_source": True,
    "member_can_update_own_source": True,
    "member_can_process_own_source": True,
    "member_can_delete_own_source": False,
    "member_can_remove_source": False,
    "member_can_create_note": True,
    "member_can_update_own_note": True,
    "member_can_delete_own_note": True,
    "member_can_delete_chat": False,
    "member_can_update_notebook": False,
}


class WorkspacePolicyRepository:
    """Named workspace permission policy queries."""

    @staticmethod
    def policy_from_row(row: Optional[dict[str, Any]]) -> dict[str, bool]:
        if not row:
            return DEFAULT_POLICY.copy()
        return {
            field: bool(row[field]) if field in row else DEFAULT_POLICY[field]
            for field in POLICY_FIELDS
        }

    @staticmethod
    async def get_workspace_policy(workspace_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT * FROM workspace_policy
            WHERE workspace_id = $workspace_id
            LIMIT 1
            """,
            {"workspace_id": ensure_record_id(workspace_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def upsert_workspace_policy(
        *,
        workspace_id: str,
        policy: dict[str, bool],
    ) -> dict[str, Any]:
        assignments = ",\n".join(f"{field} = ${field}" for field in POLICY_FIELDS)
        result = await repo_query(
            f"""
            UPSERT workspace_policy SET
                workspace_id = $workspace_id,
                {assignments},
                updated = time::now()
            WHERE workspace_id = $workspace_id
            RETURN AFTER
            """,
            {
                "workspace_id": ensure_record_id(workspace_id),
                **{field: bool(policy[field]) for field in POLICY_FIELDS},
            },
        )
        return result[0] if result else {}

    @staticmethod
    async def get_system_policy() -> Optional[dict[str, Any]]:
        result = await repo_query("SELECT * FROM workspace_system_policy:global")
        return result[0] if result else None

    @staticmethod
    async def upsert_system_policy(policy: dict[str, bool]) -> dict[str, Any]:
        assignments = ",\n".join(f"{field} = ${field}" for field in POLICY_FIELDS)
        result = await repo_query(
            f"""
            UPSERT workspace_system_policy:global SET
                {assignments},
                updated = time::now()
            RETURN AFTER
            """,
            {field: bool(policy[field]) for field in POLICY_FIELDS},
        )
        return result[0] if result else {}

    @staticmethod
    async def get_effective_policy(workspace_id: str) -> dict[str, bool]:
        workspace_policy = WorkspacePolicyRepository.policy_from_row(
            await WorkspacePolicyRepository.get_workspace_policy(workspace_id)
        )
        system_policy = WorkspacePolicyRepository.policy_from_row(
            await WorkspacePolicyRepository.get_system_policy()
        )
        return {
            field: workspace_policy[field] and system_policy[field]
            for field in POLICY_FIELDS
        }
