import time
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger
from pydantic import Field
from surreal_commands import CommandInput, CommandOutput, command

from api.services.external_api_client import ExternalApiClient
from open_notebook.database.repositories.external_api_repository import (
    ExternalApiRepository,
)
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
from open_notebook.exceptions import ExternalServiceError, InvalidInputError, NotFoundError
from open_notebook.utils.encryption import decrypt_value


def _command_id(input_data: CommandInput) -> Optional[str]:
    context = getattr(input_data, "execution_context", None)
    return str(context.command_id) if context and context.command_id else None


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _record_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        return str(value.get("id")) if value.get("id") else None
    return str(value)


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


def _artifact_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "workspace_id": _record_id(row.get("workspace_id")),
        "team_id": _record_id(row.get("team")),
        "source_id": _record_id(row.get("source")),
        "title": row.get("title"),
        "kind": row.get("kind", "markdown"),
        "content": row.get("content"),
        "data": dict(row.get("data") or {}),
        "file_url": row.get("file_url"),
        "status": row.get("status", "completed"),
        "command_id": row.get("command_id"),
        "metadata": dict(row.get("metadata") or {}),
        "created_by": _record_id(row.get("created_by")),
        "created": str(row.get("created", "")),
        "updated": str(row.get("updated", "")),
    }


async def _reserve_usage(
    *,
    actor_id: str,
    team_id: str,
    source_id: str,
    grant_id: str,
    operation: str,
    command_id: Optional[str],
) -> dict[str, Any]:
    month = _current_month()
    grant = await ExternalApiRepository.get_active_team_grant(
        team_id=team_id,
        source_id=source_id,
    )
    if not grant or str(grant.get("id")) != grant_id:
        raise ValueError("External source is not authorized for this team")

    used = await ExternalApiRepository.month_usage_count(
        grant_id=grant_id,
        month=month,
    )
    quota = int(grant.get("monthly_request_quota") or 0)
    if used >= quota:
        raise ValueError(f"External API quota exceeded: {used}/{quota} used for {month}")

    usage = await ExternalApiRepository.create_usage(
        {
            "team_id": team_id,
            "source_id": source_id,
            "grant_id": grant_id,
            "actor_id": actor_id,
            "operation": operation,
            "command_id": command_id,
            "month": month,
            "status": "reserved",
            "external_request_id": command_id,
        }
    )
    if not usage:
        raise ValueError("Failed to reserve external API usage")
    return usage


async def _mark_usage(
    usage: Optional[dict[str, Any]],
    status: str,
    error_message: Optional[str] = None,
) -> None:
    if usage and usage.get("id"):
        await ExternalApiRepository.update_usage_status(
            usage_id=str(usage["id"]),
            status=status,
            error_message=error_message,
        )


def _external_item_payload(
    raw: dict[str, Any],
    *,
    source_id: str,
    team_id: str,
    grant_id: str,
    actor_id: str,
    command_id: Optional[str],
) -> dict[str, Any]:
    external_id = raw.get("external_id") or raw.get("id") or raw.get("url")
    if not external_id:
        external_id = raw.get("title") or str(hash(str(raw)))
    return {
        "source_id": source_id,
        "team_id": team_id,
        "grant_id": grant_id,
        "external_id": str(external_id),
        "title": raw.get("title") or "Untitled",
        "summary": raw.get("summary") or raw.get("abstract"),
        "content_markdown": raw.get("content_markdown") or raw.get("content"),
        "url": raw.get("url"),
        "authors": raw.get("authors") or [],
        "published_at": raw.get("published_at"),
        "metadata": raw.get("metadata") or {},
        "raw_payload": raw,
        "created_by": actor_id,
        "command_id": command_id,
    }


class ExternalSearchInput(CommandInput):
    actor_id: str
    team_id: str
    source_id: str
    grant_id: str
    query: str
    limit: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)
    notebook_id: Optional[str] = None


class ExternalFetchInput(CommandInput):
    actor_id: str
    team_id: str
    source_id: str
    grant_id: str
    item_id: str
    external_id: str


class ExternalOutputGenerateInput(CommandInput):
    actor_id: str
    team_id: str
    source_id: str
    grant_id: str
    prompt: str
    input_text: Optional[str] = None
    item_ids: list[str] = Field(default_factory=list)
    output_kind: str = "markdown"
    options: dict[str, Any] = Field(default_factory=dict)


class ExternalApiCommandOutput(CommandOutput):
    success: bool
    operation: str
    processing_time: float
    item_count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    artifact: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


@command(
    "external_source_search",
    app="open_notebook",
    retry={"max_attempts": 1},
)
async def external_source_search_command(
    input_data: ExternalSearchInput,
) -> ExternalApiCommandOutput:
    start = time.time()
    command_id = _command_id(input_data)

    try:
        source = await ExternalApiRepository.get_source(input_data.source_id)
        if not source or not source.get("enabled", True):
            raise ValueError("External source is not available")

        client = await _client_for_source(source)
        response = await client.search_sources(
            {
                "source_key": source.get("key"),
                "query": input_data.query,
                "limit": input_data.limit,
                "filters": input_data.filters,
            }
        )
        final_response = await client.wait_for_result(response)
        if final_response.get("status") == "failed":
            raise ExternalServiceError(
                str((final_response.get("error") or {}).get("message") or "External search failed")
            )

        data = final_response.get("data") or {}
        raw_items = data.get("items") or final_response.get("items") or []
        items: list[dict[str, Any]] = []
        for raw_item in raw_items:
            item = await ExternalApiRepository.upsert_item(
                _external_item_payload(
                    raw_item,
                    source_id=input_data.source_id,
                    team_id=input_data.team_id,
                    grant_id=input_data.grant_id,
                    actor_id=input_data.actor_id,
                    command_id=command_id,
                )
            )
            if item:
                items.append(item)

        return ExternalApiCommandOutput(
            success=True,
            operation="search",
            processing_time=time.time() - start,
            item_count=len(items),
            items=items,
        )
    except TimeoutError as exc:
        return ExternalApiCommandOutput(
            success=False,
            operation="search",
            processing_time=time.time() - start,
            error_message=str(exc),
        )
    except Exception as exc:
        logger.exception(f"External source search failed: {exc}")
        return ExternalApiCommandOutput(
            success=False,
            operation="search",
            processing_time=time.time() - start,
            error_message=str(exc),
        )


@command(
    "external_source_fetch",
    app="open_notebook",
    retry={"max_attempts": 1},
)
async def external_source_fetch_command(
    input_data: ExternalFetchInput,
) -> ExternalApiCommandOutput:
    start = time.time()
    usage: Optional[dict[str, Any]] = None
    command_id = _command_id(input_data)

    try:
        source = await ExternalApiRepository.get_source(input_data.source_id)
        if not source or not source.get("enabled", True):
            raise ValueError("External source is not available")

        item = await ExternalApiRepository.get_item(input_data.item_id)
        if not item:
            raise ValueError("External source item not found")

        usage = await _reserve_usage(
            actor_id=input_data.actor_id,
            team_id=input_data.team_id,
            source_id=input_data.source_id,
            grant_id=input_data.grant_id,
            operation="fetch",
            command_id=command_id,
        )

        client = await _client_for_source(source)
        response = await client.fetch_source(
            {
                "source_key": source.get("key"),
                "external_id": input_data.external_id,
                "metadata": item.get("metadata") or {},
            }
        )
        final_response = await client.wait_for_result(response)
        if final_response.get("status") == "failed":
            raise ExternalServiceError(
                str((final_response.get("error") or {}).get("message") or "External fetch failed")
            )

        data = final_response.get("data") or {}
        fetched = await ExternalApiRepository.upsert_item(
            {
                **_external_item_payload(
                    {
                        **item,
                        **data,
                        "external_id": input_data.external_id,
                    },
                    source_id=input_data.source_id,
                    team_id=input_data.team_id,
                    grant_id=input_data.grant_id,
                    actor_id=input_data.actor_id,
                    command_id=command_id,
                ),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        await _mark_usage(usage, "completed")
        return ExternalApiCommandOutput(
            success=True,
            operation="fetch",
            processing_time=time.time() - start,
            item_count=1,
            items=[fetched] if fetched else [],
        )
    except TimeoutError as exc:
        await _mark_usage(usage, "timeout", str(exc))
        return ExternalApiCommandOutput(
            success=False,
            operation="fetch",
            processing_time=time.time() - start,
            error_message=str(exc),
        )
    except Exception as exc:
        await _mark_usage(usage, "failed", str(exc))
        logger.exception(f"External source fetch failed: {exc}")
        return ExternalApiCommandOutput(
            success=False,
            operation="fetch",
            processing_time=time.time() - start,
            error_message=str(exc),
        )


@command(
    "external_output_generate",
    app="open_notebook",
    retry={"max_attempts": 1},
)
async def external_output_generate_command(
    input_data: ExternalOutputGenerateInput,
) -> ExternalApiCommandOutput:
    start = time.time()
    usage: Optional[dict[str, Any]] = None
    command_id = _command_id(input_data)

    try:
        source = await ExternalApiRepository.get_source(input_data.source_id)
        if not source or not source.get("enabled", True):
            raise ValueError("External source is not available")

        items: list[dict[str, Any]] = []
        for item_id in input_data.item_ids:
            item = await ExternalApiRepository.get_item(item_id)
            if item:
                items.append(item)

        usage = await _reserve_usage(
            actor_id=input_data.actor_id,
            team_id=input_data.team_id,
            source_id=input_data.source_id,
            grant_id=input_data.grant_id,
            operation="generate",
            command_id=command_id,
        )

        client = await _client_for_source(source)
        response = await client.generate_output(
            {
                "source_key": source.get("key"),
                "prompt": input_data.prompt,
                "input_text": input_data.input_text,
                "items": items,
                "output_kind": input_data.output_kind,
                "options": input_data.options,
            }
        )
        final_response = await client.wait_for_result(response)
        if final_response.get("status") == "failed":
            raise ExternalServiceError(
                str((final_response.get("error") or {}).get("message") or "External output generation failed")
            )

        data = final_response.get("data") or {}
        workspace = await WorkspaceRepository.get_team_workspace(input_data.team_id)
        artifact = await ExternalApiRepository.create_output_artifact(
            {
                "workspace_id": str(workspace["id"]) if workspace else None,
                "team_id": input_data.team_id,
                "source_id": input_data.source_id,
                "grant_id": input_data.grant_id,
                "created_by": input_data.actor_id,
                "title": data.get("title"),
                "kind": data.get("kind") or input_data.output_kind,
                "content": data.get("content"),
                "data": data.get("data") or {},
                "file_url": data.get("file_url"),
                "status": "completed",
                "command_id": command_id,
                "metadata": data.get("metadata") or {},
            }
        )

        await _mark_usage(usage, "completed")
        return ExternalApiCommandOutput(
            success=True,
            operation="generate",
            processing_time=time.time() - start,
            artifact=_artifact_payload(artifact) if artifact else None,
        )
    except TimeoutError as exc:
        await _mark_usage(usage, "timeout", str(exc))
        return ExternalApiCommandOutput(
            success=False,
            operation="generate",
            processing_time=time.time() - start,
            error_message=str(exc),
        )
    except Exception as exc:
        await _mark_usage(usage, "failed", str(exc))
        logger.exception(f"External output generation failed: {exc}")
        return ExternalApiCommandOutput(
            success=False,
            operation="generate",
            processing_time=time.time() - start,
            error_message=str(exc),
        )
