from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from api.auth import CurrentUser
from api.command_service import CommandService
from api.models import (
    ExternalApiCommandResponse,
    ExternalApiConnectionCreate,
    ExternalApiConnectionListResponse,
    ExternalApiConnectionResponse,
    ExternalApiConnectionTestResponse,
    ExternalApiFetchRequest,
    ExternalApiSearchRequest,
    ExternalApiUsageItem,
    ExternalApiUsageResponse,
    ExternalAvailableSourceListResponse,
    ExternalAvailableSourceResponse,
    ExternalItemNotebookReferenceRequest,
    ExternalItemSnapshotRequest,
    ExternalItemSnapshotResponse,
    ExternalOutputGenerateRequest,
    ExternalSourceCreate,
    ExternalSourceItemResponse,
    ExternalSourceTeamGrantListResponse,
    ExternalSourceListResponse,
    ExternalSourceResponse,
    ExternalSourceTeamGrantCreate,
    ExternalSourceTeamGrantResponse,
    ExternalSourceTeamGrantUpdate,
    OutputArtifactResponse,
    SourceCreate,
)
from api.services.external_api_client import ExternalApiClient
from api.services.source_service import create_source_and_queue_processing
from open_notebook.database.repositories.external_api_repository import (
    ExternalApiRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import (
    ExternalServiceError,
    InvalidInputError,
    NotFoundError,
    RateLimitError,
)
from open_notebook.utils.encryption import decrypt_value, encrypt_value


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _record_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        return str(value.get("id")) if value.get("id") else None
    return str(value)


def _connection_response(row: dict[str, Any]) -> ExternalApiConnectionResponse:
    return ExternalApiConnectionResponse(
        id=str(row.get("id", "")),
        name=row.get("name", ""),
        target_type=row.get("target_type") or "source",
        base_url=row.get("base_url", ""),
        manifest=row.get("manifest"),
        enabled=bool(row.get("enabled", True)),
        timeout_seconds=int(row.get("timeout_seconds") or 30),
        api_key_configured=bool(row.get("api_key")),
        created_by=_record_id(row.get("created_by")),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _source_response(row: dict[str, Any]) -> ExternalSourceResponse:
    connection = row.get("connection")
    connection_id = _record_id(connection) or ""
    connection_name = connection.get("name") if isinstance(connection, dict) else None
    return ExternalSourceResponse(
        id=str(row.get("id", "")),
        connection_id=connection_id,
        connection_name=connection_name,
        name=row.get("name", ""),
        key=row.get("key", ""),
        description=row.get("description"),
        capabilities=list(row.get("capabilities") or []),
        config=dict(row.get("config") or {}),
        enabled=bool(row.get("enabled", True)),
        created_by=_record_id(row.get("created_by")),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _grant_response(row: dict[str, Any]) -> ExternalSourceTeamGrantResponse:
    source = row.get("source")
    team = row.get("team")
    return ExternalSourceTeamGrantResponse(
        id=str(row.get("id", "")),
        source_id=_record_id(source) or "",
        source_name=source.get("name") if isinstance(source, dict) else None,
        team_id=_record_id(team) or "",
        team_name=team.get("name") if isinstance(team, dict) else None,
        monthly_request_quota=int(row.get("monthly_request_quota") or 0),
        enabled=bool(row.get("enabled", True)),
        created_by=_record_id(row.get("created_by")),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _item_response(row: dict[str, Any]) -> ExternalSourceItemResponse:
    return ExternalSourceItemResponse(
        id=str(row.get("id", "")),
        source_id=_record_id(row.get("source")) or "",
        team_id=_record_id(row.get("team")) or "",
        external_id=str(row.get("external_id", "")),
        title=row.get("title") or "Untitled",
        summary=row.get("summary"),
        content_markdown=row.get("content_markdown"),
        url=row.get("url"),
        authors=list(row.get("authors") or []),
        published_at=row.get("published_at"),
        metadata=dict(row.get("metadata") or {}),
        fetched_at=str(row.get("fetched_at")) if row.get("fetched_at") else None,
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _artifact_response(row: dict[str, Any]) -> OutputArtifactResponse:
    return OutputArtifactResponse(
        id=str(row.get("id", "")),
        workspace_id=_record_id(row.get("workspace_id")),
        team_id=_record_id(row.get("team")),
        source_id=_record_id(row.get("source")),
        title=row.get("title"),
        kind=row.get("kind", "markdown"),
        content=row.get("content"),
        data=dict(row.get("data") or {}),
        file_url=row.get("file_url"),
        status=row.get("status", "completed"),
        command_id=row.get("command_id"),
        metadata=dict(row.get("metadata") or {}),
        created_by=_record_id(row.get("created_by")),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


async def _ensure_team_member(team_id: str, actor: CurrentUser) -> None:
    if actor.role == "admin":
        return
    member = await TeamRepository.get_member(team_id, actor.id)
    if not member or member.get("status") != "active":
        raise PermissionError("Team membership required")


async def _ensure_team_manager(team_id: str, actor: CurrentUser) -> None:
    if actor.role == "admin":
        return
    member = await TeamRepository.get_member(team_id, actor.id)
    if not member or member.get("status") != "active" or member.get("role") not in {
        "owner",
        "admin",
    }:
        raise PermissionError("Team owner or admin privileges required")


async def _ensure_team_workspace_create_allowed(team_id: str, actor: CurrentUser) -> None:
    workspace = await WorkspaceRepository.get_team_workspace(team_id)
    if not workspace:
        raise NotFoundError("Team workspace not found")
    role = await WorkspaceRepository.current_user_role(
        workspace_id=str(workspace["id"]),
        user_id=actor.id,
    )
    current_role = role.get("current_user_role") if role else None
    if current_role not in {"owner", "admin", "member"}:
        raise PermissionError("Workspace creation permission required")


async def _active_grant_or_error(team_id: str, source_id: str) -> dict[str, Any]:
    grant = await ExternalApiRepository.get_active_team_grant(
        team_id=team_id,
        source_id=source_id,
    )
    if not grant:
        raise PermissionError("External source is not authorized for this team")
    return grant


async def _ensure_quota_available(grant: dict[str, Any], *, month: Optional[str] = None) -> int:
    month = month or current_month()
    quota = int(grant.get("monthly_request_quota") or 0)
    used = await ExternalApiRepository.month_usage_count(
        grant_id=str(grant["id"]),
        month=month,
    )
    if quota <= used:
        raise RateLimitError(f"External API quota exceeded: {used}/{quota} used for {month}")
    return used


async def create_connection_use_case(
    request: ExternalApiConnectionCreate,
    *,
    actor: CurrentUser,
) -> ExternalApiConnectionResponse:
    row = await ExternalApiRepository.create_connection(
        {
            "name": request.name,
            "target_type": request.target_type,
            "base_url": request.base_url,
            "api_key": encrypt_value(request.api_key),
            "manifest": request.manifest,
            "enabled": request.enabled,
            "timeout_seconds": request.timeout_seconds,
            "created_by": actor.id,
        }
    )
    if not row:
        raise InvalidInputError("Failed to create external API connection")
    return _connection_response(row)


async def list_connections_use_case() -> ExternalApiConnectionListResponse:
    rows = await ExternalApiRepository.list_connections()
    return ExternalApiConnectionListResponse(
        items=[_connection_response(row) for row in rows]
    )


async def test_connection_use_case(connection_id: str) -> ExternalApiConnectionTestResponse:
    connection = await ExternalApiRepository.get_connection(connection_id)
    if not connection:
        raise NotFoundError("External API connection not found")

    client = ExternalApiClient(
        base_url=connection["base_url"],
        api_key=decrypt_value(connection["api_key"]),
        timeout_seconds=int(connection.get("timeout_seconds") or 30),
    )
    try:
        manifest = await client.get_manifest()
        health = await client.health()
        await ExternalApiRepository.update_connection(connection_id, {"manifest": manifest})
        return ExternalApiConnectionTestResponse(
            ok=True,
            status=str(health.get("status", "ok")),
            manifest=manifest,
            health=health,
        )
    except Exception as exc:
        return ExternalApiConnectionTestResponse(
            ok=False,
            status="failed",
            message=str(exc),
        )


async def create_source_use_case(
    request: ExternalSourceCreate,
    *,
    actor: CurrentUser,
) -> ExternalSourceResponse:
    connection = await ExternalApiRepository.get_connection(request.connection_id)
    if not connection:
        raise NotFoundError("External API connection not found")
    if (connection.get("target_type") or "source") != "source":
        raise InvalidInputError("Only source API connections can define external sources")
    row = await ExternalApiRepository.create_source(
        {
            "connection_id": request.connection_id,
            "name": request.name,
            "key": request.key,
            "description": request.description,
            "capabilities": ["search", "fetch"],
            "config": request.config,
            "enabled": request.enabled,
            "created_by": actor.id,
        }
    )
    if not row:
        raise InvalidInputError("Failed to create external source")
    row["connection"] = connection
    return _source_response(row)


async def list_sources_use_case() -> ExternalSourceListResponse:
    rows = await ExternalApiRepository.list_sources()
    return ExternalSourceListResponse(items=[_source_response(row) for row in rows])


async def create_team_grant_use_case(
    source_id: str,
    request: ExternalSourceTeamGrantCreate,
    *,
    actor: CurrentUser,
) -> ExternalSourceTeamGrantResponse:
    source = await ExternalApiRepository.get_source(source_id)
    if not source:
        raise NotFoundError("External source not found")
    team = await TeamRepository.get_team(request.team_id)
    if not team:
        raise NotFoundError("Team not found")
    if team.get("type") == "system":
        raise InvalidInputError("System teams cannot receive external source grants")
    row = await ExternalApiRepository.create_team_grant(
        {
            "source_id": source_id,
            "team_id": request.team_id,
            "monthly_request_quota": request.monthly_request_quota,
            "enabled": request.enabled,
            "created_by": actor.id,
        }
    )
    if not row:
        raise InvalidInputError("Failed to create external source team grant")
    row["source"] = source
    row["team"] = team
    return _grant_response(row)


async def list_team_grants_use_case(source_id: str) -> ExternalSourceTeamGrantListResponse:
    source = await ExternalApiRepository.get_source(source_id)
    if not source:
        raise NotFoundError("External source not found")
    rows = await ExternalApiRepository.list_team_grants_for_source(source_id)
    return ExternalSourceTeamGrantListResponse(items=[_grant_response(row) for row in rows])


async def update_team_grant_use_case(
    grant_id: str,
    request: ExternalSourceTeamGrantUpdate,
) -> ExternalSourceTeamGrantResponse:
    data = request.model_dump(exclude_unset=True)
    if not data:
        grant = await ExternalApiRepository.get_team_grant(grant_id)
    else:
        grant = await ExternalApiRepository.update_team_grant(grant_id, data)
    if not grant:
        raise NotFoundError("External source team grant not found")
    fetched = await ExternalApiRepository.get_team_grant(grant_id)
    return _grant_response(fetched or grant)


async def list_available_sources_use_case(
    *,
    team_id: str,
    actor: CurrentUser,
) -> ExternalAvailableSourceListResponse:
    await _ensure_team_member(team_id, actor)
    month = current_month()
    rows = await ExternalApiRepository.list_available_sources(team_id)
    items: list[ExternalAvailableSourceResponse] = []
    for grant in rows:
        source = grant.get("source") if isinstance(grant.get("source"), dict) else {}
        source_response = _source_response(source)
        used = await ExternalApiRepository.month_usage_count(
            grant_id=str(grant["id"]),
            month=month,
        )
        items.append(
            ExternalAvailableSourceResponse(
                **source_response.model_dump(),
                grant_id=str(grant.get("id", "")),
                team_id=team_id,
                monthly_request_quota=int(grant.get("monthly_request_quota") or 0),
                current_month_usage=used,
            )
        )
    return ExternalAvailableSourceListResponse(items=items)


async def submit_search_use_case(
    source_id: str,
    request: ExternalApiSearchRequest,
    *,
    actor: CurrentUser,
) -> ExternalApiCommandResponse:
    await _ensure_team_member(request.team_id, actor)
    grant = await _active_grant_or_error(request.team_id, source_id)
    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "external_source_search",
        {
            "actor_id": actor.id,
            "team_id": request.team_id,
            "source_id": source_id,
            "grant_id": str(grant["id"]),
            "query": request.query,
            "limit": request.limit,
            "filters": request.filters,
            "notebook_id": request.notebook_id,
        },
    )
    return ExternalApiCommandResponse(
        command_id=command_id,
        message="External source search queued",
    )


async def submit_fetch_use_case(
    item_id: str,
    request: ExternalApiFetchRequest,
    *,
    actor: CurrentUser,
) -> ExternalApiCommandResponse:
    await _ensure_team_member(request.team_id, actor)
    item = await ExternalApiRepository.get_item(item_id)
    if not item:
        raise NotFoundError("External source item not found")
    source_id = _record_id(item.get("source"))
    if not source_id:
        raise InvalidInputError("External item has no source")
    grant = await _active_grant_or_error(request.team_id, source_id)
    await _ensure_quota_available(grant)
    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "external_source_fetch",
        {
            "actor_id": actor.id,
            "team_id": request.team_id,
            "source_id": source_id,
            "grant_id": str(grant["id"]),
            "item_id": item_id,
            "external_id": item.get("external_id"),
        },
    )
    return ExternalApiCommandResponse(
        command_id=command_id,
        message="External source fetch queued",
    )


async def reference_item_use_case(
    item_id: str,
    request: ExternalItemNotebookReferenceRequest,
    *,
    actor: CurrentUser,
) -> ExternalSourceItemResponse:
    item = await ExternalApiRepository.get_item(item_id)
    if not item:
        raise NotFoundError("External source item not found")
    team_id = _record_id(item.get("team"))
    source_id = _record_id(item.get("source"))
    if not team_id or not source_id:
        raise InvalidInputError("External item is missing team or source context")
    await _ensure_team_member(team_id, actor)
    await ExternalApiRepository.create_notebook_item_reference(
        item_id=item_id,
        notebook_id=request.notebook_id,
        team_id=team_id,
        source_id=source_id,
        created_by=actor.id,
    )
    return _item_response(item)


async def snapshot_item_use_case(
    item_id: str,
    request: ExternalItemSnapshotRequest,
    *,
    actor: CurrentUser,
) -> ExternalItemSnapshotResponse:
    item = await ExternalApiRepository.get_item(item_id)
    if not item:
        raise NotFoundError("External source item not found")
    team_id = _record_id(item.get("team"))
    source_id = _record_id(item.get("source"))
    if not team_id or not source_id:
        raise InvalidInputError("External item is missing team or source context")
    await _ensure_team_member(team_id, actor)

    notebook = await Notebook.get(request.notebook_id)
    external_source = await ExternalApiRepository.get_source(source_id)
    content = item.get("content_markdown") or item.get("summary") or item.get("title")
    if not content:
        raise InvalidInputError("External item has no content to snapshot")

    source_response = await create_source_and_queue_processing(
        SourceCreate(
            type="text",
            title=item.get("title") or "External source snapshot",
            content=content,
            external_source_name=(external_source or {}).get("name"),
            notebooks=[request.notebook_id],
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            embed=request.embed,
        ),
        user_id=actor.id,
        actor=actor,
    )
    await ExternalApiRepository.create_notebook_item_reference(
        item_id=item_id,
        notebook_id=request.notebook_id,
        team_id=team_id,
        source_id=source_id,
        created_by=actor.id,
    )
    return ExternalItemSnapshotResponse(
        item_id=item_id,
        source_id=source_id,
        notebook_id=request.notebook_id,
        lumina_source=source_response,
    )


async def submit_output_generate_use_case(
    request: ExternalOutputGenerateRequest,
    *,
    actor: CurrentUser,
) -> ExternalApiCommandResponse:
    await _ensure_team_member(request.team_id, actor)
    await _ensure_team_workspace_create_allowed(request.team_id, actor)
    grant = await _active_grant_or_error(request.team_id, request.source_id)
    await _ensure_quota_available(grant)
    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "external_output_generate",
        {
            "actor_id": actor.id,
            "team_id": request.team_id,
            "source_id": request.source_id,
            "grant_id": str(grant["id"]),
            "prompt": request.prompt,
            "input_text": request.input_text,
            "item_ids": request.item_ids,
            "output_kind": request.output_kind,
            "options": request.options,
        },
    )
    return ExternalApiCommandResponse(
        command_id=command_id,
        message="External output generation queued",
    )


async def command_status_use_case(command_id: str) -> dict[str, Any]:
    return await CommandService.get_command_status(command_id)


async def usage_use_case(
    *,
    team_id: str,
    actor: CurrentUser,
    month: Optional[str] = None,
) -> ExternalApiUsageResponse:
    await _ensure_team_manager(team_id, actor)
    month = month or current_month()
    rows = await ExternalApiRepository.usage_summary(team_id=team_id, month=month)
    grants = await ExternalApiRepository.list_available_sources(team_id)
    quotas = {
        _record_id(grant.get("source")): int(grant.get("monthly_request_quota") or 0)
        for grant in grants
    }
    items: list[ExternalApiUsageItem] = []
    for row in rows:
        source = row.get("source")
        source_id = _record_id(source) or ""
        items.append(
            ExternalApiUsageItem(
                source_id=source_id,
                source_name=source.get("name") if isinstance(source, dict) else None,
                operation=row.get("operation"),
                month=month,
                requests=int(row.get("requests") or 0),
                quota=quotas.get(source_id, 0),
            )
        )
    return ExternalApiUsageResponse(team_id=team_id, month=month, items=items)


async def _client_for_source(source: dict[str, Any]) -> ExternalApiClient:
    connection = source.get("connection")
    if not isinstance(connection, dict):
        connection_id = _record_id(connection)
        if not connection_id:
            raise InvalidInputError("External source has no connection")
        connection = await ExternalApiRepository.get_connection(connection_id)
    if not connection:
        raise NotFoundError("External API connection not found")
    if not connection.get("enabled", True):
        raise ExternalServiceError("External API connection is disabled")
    return ExternalApiClient(
        base_url=connection["base_url"],
        api_key=decrypt_value(connection["api_key"]),
        timeout_seconds=int(connection.get("timeout_seconds") or 30),
    )


__all__ = [
    "ExternalApiRepository",
    "_client_for_source",
    "_item_response",
    "_artifact_response",
    "current_month",
]
