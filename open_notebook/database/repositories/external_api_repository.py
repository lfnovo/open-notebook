from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

from open_notebook.database.repository import (
    ensure_record_id,
    repo_query,
    repo_update,
    repo_upsert,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stable_item_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"external_source_item:{digest}"


class ExternalApiRepository:
    """Named queries for system-managed third-party API integrations."""

    @staticmethod
    async def create_connection(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE external_api_connection SET
                name = $name,
                target_type = $target_type,
                base_url = $base_url,
                api_key = $api_key,
                manifest = $manifest,
                enabled = $enabled,
                timeout_seconds = $timeout_seconds,
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
    async def list_connections() -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT *
            FROM external_api_connection
            ORDER BY created DESC
            """
        )

    @staticmethod
    async def get_connection(connection_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            "SELECT * FROM $connection_id LIMIT 1",
            {"connection_id": ensure_record_id(connection_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def update_connection(connection_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        rows = await repo_update("external_api_connection", connection_id, data)
        return rows[0] if rows else None

    @staticmethod
    async def create_source(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE external_source SET
                connection = $connection,
                name = $name,
                key = $key,
                description = $description,
                capabilities = $capabilities,
                config = $config,
                enabled = $enabled,
                created_by = $created_by,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                **data,
                "connection": ensure_record_id(data["connection_id"]),
                "created_by": ensure_record_id(data["created_by"])
                if data.get("created_by")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def list_sources() -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT *
            FROM external_source
            ORDER BY created DESC
            FETCH connection
            """
        )

    @staticmethod
    async def get_source(source_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM $source_id
            LIMIT 1
            FETCH connection
            """,
            {"source_id": ensure_record_id(source_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def create_team_grant(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE external_source_team_grant SET
                source = $source,
                team = $team,
                monthly_request_quota = $monthly_request_quota,
                enabled = $enabled,
                created_by = $created_by,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                **data,
                "source": ensure_record_id(data["source_id"]),
                "team": ensure_record_id(data["team_id"]),
                "created_by": ensure_record_id(data["created_by"])
                if data.get("created_by")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def update_team_grant(grant_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        rows = await repo_update("external_source_team_grant", grant_id, data)
        return rows[0] if rows else None

    @staticmethod
    async def get_team_grant(grant_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM $grant_id
            LIMIT 1
            FETCH source, team
            """,
            {"grant_id": ensure_record_id(grant_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def list_team_grants_for_source(source_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT *
            FROM external_source_team_grant
            WHERE source = $source_id
            ORDER BY created DESC
            FETCH source, team
            """,
            {"source_id": ensure_record_id(source_id)},
        )

    @staticmethod
    async def get_active_team_grant(
        *,
        team_id: str,
        source_id: str,
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM external_source_team_grant
            WHERE team = $team_id
                AND source = $source_id
                AND enabled = true
            LIMIT 1
            """,
            {
                "team_id": ensure_record_id(team_id),
                "source_id": ensure_record_id(source_id),
            },
        )
        return result[0] if result else None

    @staticmethod
    async def list_available_sources(team_id: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT *
            FROM external_source_team_grant
            WHERE team = $team_id
                AND enabled = true
                AND source.enabled = true
                AND source.connection.enabled = true
            ORDER BY source.name ASC
            FETCH source, source.connection
            """,
            {"team_id": ensure_record_id(team_id)},
        )

    @staticmethod
    async def month_usage_count(*, grant_id: str, month: str) -> int:
        result = await repo_query(
            """
            SELECT count() AS count
            FROM external_api_usage
            WHERE grant = $grant_id AND month = $month AND operation != 'search'
            GROUP ALL
            """,
            {"grant_id": ensure_record_id(grant_id), "month": month},
        )
        if not result:
            return 0
        return int(result[0].get("count") or 0)

    @staticmethod
    async def create_usage(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE external_api_usage SET
                team = $team,
                source = $source,
                grant = $grant,
                actor = $actor,
                operation = $operation,
                command_id = $command_id,
                month = $month,
                status = $status,
                external_request_id = $external_request_id,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                **data,
                "team": ensure_record_id(data["team_id"]),
                "source": ensure_record_id(data["source_id"]),
                "grant": ensure_record_id(data["grant_id"]),
                "actor": ensure_record_id(data["actor_id"])
                if data.get("actor_id")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def update_usage_status(
        *,
        usage_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        rows = await repo_update(
            "external_api_usage",
            usage_id,
            {"status": status, "error_message": error_message},
        )
        return rows[0] if rows else None

    @staticmethod
    async def upsert_item(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        item_id = _stable_item_id(
            data["source_id"],
            data["team_id"],
            str(data["external_id"]),
        )
        payload = {
            **data,
            "source": ensure_record_id(data["source_id"]),
            "team": ensure_record_id(data["team_id"]),
            "grant": ensure_record_id(data["grant_id"]) if data.get("grant_id") else None,
            "created_by": ensure_record_id(data["created_by"])
            if data.get("created_by")
            else None,
            "updated": _now(),
        }
        payload.setdefault("created", _now())
        payload.pop("source_id", None)
        payload.pop("team_id", None)
        payload.pop("grant_id", None)
        rows = await repo_upsert(None, item_id, payload)
        return rows[0] if rows else None

    @staticmethod
    async def get_item(item_id: str) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            SELECT *
            FROM $item_id
            LIMIT 1
            FETCH source
            """,
            {"item_id": ensure_record_id(item_id)},
        )
        return result[0] if result else None

    @staticmethod
    async def create_notebook_item_reference(
        *,
        item_id: str,
        notebook_id: str,
        team_id: str,
        source_id: str,
        created_by: str,
    ) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            RELATE $item_id->notebook_external_item->$notebook_id SET
                team = $team,
                source = $source,
                created_by = $created_by,
                created = time::now()
            RETURN AFTER
            """,
            {
                "item_id": ensure_record_id(item_id),
                "notebook_id": ensure_record_id(notebook_id),
                "team": ensure_record_id(team_id),
                "source": ensure_record_id(source_id),
                "created_by": ensure_record_id(created_by),
            },
        )
        return result[0] if result else None

    @staticmethod
    async def create_output_artifact(data: dict[str, Any]) -> Optional[dict[str, Any]]:
        result = await repo_query(
            """
            CREATE output_artifact SET
                workspace_id = $workspace_id,
                team = $team,
                source = $source,
                grant = $grant,
                created_by = $created_by,
                title = $title,
                kind = $kind,
                content = $content,
                data = $data,
                file_url = $file_url,
                status = $status,
                command_id = $command_id,
                metadata = $metadata,
                created = time::now(),
                updated = time::now()
            RETURN AFTER
            """,
            {
                **data,
                "workspace_id": ensure_record_id(data["workspace_id"])
                if data.get("workspace_id")
                else None,
                "team": ensure_record_id(data["team_id"]) if data.get("team_id") else None,
                "source": ensure_record_id(data["source_id"])
                if data.get("source_id")
                else None,
                "grant": ensure_record_id(data["grant_id"]) if data.get("grant_id") else None,
                "created_by": ensure_record_id(data["created_by"])
                if data.get("created_by")
                else None,
            },
        )
        return result[0] if result else None

    @staticmethod
    async def usage_summary(*, team_id: str, month: str) -> list[dict[str, Any]]:
        return await repo_query(
            """
            SELECT
                source,
                operation,
                month,
                count() AS requests
            FROM external_api_usage
            WHERE team = $team_id AND month = $month
            GROUP BY source, operation, month
            FETCH source
            """,
            {"team_id": ensure_record_id(team_id), "month": month},
        )
