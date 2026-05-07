from typing import Any

from api.models import AssetModel, ResourceCapabilities, SourceListResponse


def command_fields_from_fetched_command(
    command: Any,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    """Extract list response command fields from a SurrealDB FETCH result."""
    command_id = None
    status = None
    processing_info = None

    if command and isinstance(command, dict):
        command_id = str(command.get("id")) if command.get("id") else None
        status = command.get("status")
        result_data = command.get("result")
        execution_metadata = (
            result_data.get("execution_metadata", {})
            if isinstance(result_data, dict)
            else {}
        )
        processing_info = {
            "started_at": execution_metadata.get("started_at"),
            "completed_at": execution_metadata.get("completed_at"),
            "error": command.get("error_message"),
        }
    elif command:
        command_id = str(command)
        status = "unknown"

    return command_id, status, processing_info


def source_list_response_from_row(
    row: dict[str, Any],
    *,
    capabilities: ResourceCapabilities | None = None,
) -> SourceListResponse:
    """Build a SourceListResponse from a source list query row."""
    command_id, status, processing_info = command_fields_from_fetched_command(
        row.get("command")
    )

    return SourceListResponse(
        id=row["id"],
        title=row.get("title"),
        topics=row.get("topics") or [],
        asset=AssetModel(
            file_path=row["asset"].get("file_path") if row.get("asset") else None,
            url=row["asset"].get("url") if row.get("asset") else None,
        )
        if row.get("asset")
        else None,
        embedded=row.get("embedded", False),
        embedded_chunks=0,
        kg_extracted=row.get("kg_extracted", False),
        insights_count=row.get("insights_count", 0),
        reference_count=row.get("reference_count", 0),
        view_count=row.get("view_count", 0) or 0,
        created=str(row["created"]),
        updated=str(row["updated"]),
        command_id=command_id,
        status=status,
        processing_info=processing_info,
        owner_id=row.get("owner_id"),
        creator_username=row.get("creator_username"),
        workspace_id=str(row["workspace_id"]) if row.get("workspace_id") else None,
        visibility=row.get("visibility", "private"),
        capabilities=capabilities or ResourceCapabilities(),
    )
