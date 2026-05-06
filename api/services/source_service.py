"""Source application use cases.

Keep FastAPI-specific request and response handling in routers; this module
owns source orchestration that can be tested without HTTP objects.
"""

import os
from pathlib import Path
from typing import Any

from loguru import logger
from surreal_commands import get_command_status

from api.command_service import CommandService
from api.models import (
    AssetModel,
    CreateSourceInsightRequest,
    InsightCreationResponse,
    SourceCreate,
    SourceListResponse,
    SourceResponse,
    SourceStatusResponse,
    SourceUpdate,
)
from api.services import command_lifecycle
from api.services.share_service import can_read_resource
from api.services.source_permissions import (
    check_source_access,
    check_source_ownership,
)
from api.services.source_processing import (
    SOURCE_PROCESSING_TIMEOUT_MESSAGE,
    mark_command_failed,
    submit_process_source_command,
)
from api.services.source_responses import source_list_response_from_row
from api.services.team_context_service import resolve_resource_team_context
from api.services.workspace_service import resolve_workspace_id_for_user
from commands.source_commands import SourceProcessingInput
from open_notebook.ai.model_resolution import resolve_default_model_id
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.database.repositories.source_repository import SourceRepository
from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.notebook import Asset, Notebook, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError, NotFoundError


def build_source_content_state(
    source_data: SourceCreate,
    *,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Build processing input for a source create request."""
    if source_data.type == "link":
        if not source_data.url:
            raise InvalidInputError("URL is required for link type")
        return {"url": source_data.url}

    if source_data.type == "upload":
        final_file_path = file_path or source_data.file_path
        if not final_file_path:
            raise InvalidInputError(
                "File upload or file_path is required for upload type"
            )

        uploads_resolved = Path(UPLOADS_FOLDER).resolve()
        file_resolved = Path(final_file_path).resolve()
        if not str(file_resolved).startswith(str(uploads_resolved) + os.sep):
            raise InvalidInputError(
                "Invalid file path: must be within the uploads directory"
            )

        return {
            "file_path": final_file_path,
            "delete_source": source_data.delete_source,
        }

    if source_data.type == "text":
        if not source_data.content:
            raise InvalidInputError("Content is required for text type")
        return {"content": source_data.content}

    raise InvalidInputError("Invalid source type. Must be link, upload, or text")


async def resolve_source_team_context(notebook_ids: list[str] | None) -> str | None:
    """Infer one team context from selected notebooks, if unambiguous."""
    team_ids = {
        team_id
        for team_id in [
            await resolve_resource_team_context(
                resource_type="notebook",
                resource_id=notebook_id,
            )
            for notebook_id in notebook_ids or []
        ]
        if team_id
    }
    return next(iter(team_ids)) if len(team_ids) == 1 else None


async def resolve_source_workspace_id(
    source_data: SourceCreate,
    *,
    user_id: str | None,
) -> str | None:
    if source_data.workspace_id:
        return source_data.workspace_id

    workspace_ids = set()
    for notebook_id in source_data.notebooks or []:
        notebook = await Notebook.get(notebook_id)
        workspace_id = getattr(notebook, "workspace_id", None)
        workspace_id_str = str(workspace_id) if workspace_id else None
        if workspace_id_str and workspace_id_str.startswith("workspace:"):
            workspace_ids.add(workspace_id_str)
    if len(workspace_ids) == 1:
        return next(iter(workspace_ids))

    return await resolve_workspace_id_for_user(user_id=user_id, requested_workspace_id=None)


async def validate_source_create_request(
    source_data: SourceCreate,
    *,
    team_id: str | None = None,
) -> list[str]:
    """Validate related records and model defaults for source processing."""
    for notebook_id in source_data.notebooks or []:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise NotFoundError(f"Notebook {notebook_id} not found")

    transformation_ids = source_data.transformations or []
    for transformation_id in transformation_ids:
        transformation = await Transformation.get(transformation_id)
        if not transformation:
            raise NotFoundError(f"Transformation {transformation_id} not found")

    if source_data.embed and not await resolve_default_model_id(
        "embedding",
        team_id=team_id,
    ):
        raise InvalidInputError(
            "Cannot process source: No default embedding model configured. "
            "Please configure one in Settings -> Models."
        )

    if transformation_ids and not await resolve_default_model_id(
        "transformation",
        team_id=team_id,
    ):
        raise InvalidInputError(
            "Cannot process source: No default transformation or chat model "
            "configured. Please configure one in Settings -> Models."
        )

    if not await resolve_default_model_id("tools", team_id=team_id):
        raise InvalidInputError(
            "Cannot process source: No default tools or chat model configured "
            "for Knowledge Graph extraction. Please configure one in Settings -> Models."
        )

    return transformation_ids


def build_source_asset(
    source_data: SourceCreate,
    *,
    file_path: str | None = None,
) -> Asset | None:
    """Build the persisted source asset before async processing starts."""
    if source_data.type == "link":
        return Asset(url=source_data.url)
    if source_data.type == "upload":
        return Asset(file_path=file_path or source_data.file_path)
    return None


def source_response_for_queued_processing(
    source: Source,
    *,
    command_id: str,
    notebooks: list[str] | None = None,
) -> SourceResponse:
    asset = (
        AssetModel(
            file_path=source.asset.file_path if source.asset else None,
            url=source.asset.url if source.asset else None,
        )
        if source.asset
        else None
    )

    return SourceResponse(
        id=source.id or "",
        title=source.title,
        topics=source.topics or [],
        asset=asset,
        full_text=source.full_text,
        embedded=False,
        embedded_chunks=0,
        kg_extracted=False,
        created=str(source.created),
        updated=str(source.updated),
        command_id=command_id,
        status="new",
        processing_info={"async": True, "queued": True},
        notebooks=notebooks,
        owner_id=source.owner_id,
        visibility=source.visibility,
        workspace_id=str(source.workspace_id) if source.workspace_id else None,
    )


def is_source_file_available(source: Source) -> bool | None:
    """Return whether an uploaded source file is still available on disk."""
    if not source.asset or not source.asset.file_path:
        return None

    file_path = source.asset.file_path
    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        return False

    return os.path.exists(resolved_path)


async def source_response_from_source(
    source: Source,
    *,
    notebooks: list[str] | None = None,
    command_id: str | None = None,
    status: str | None = None,
    processing_info: dict[str, Any] | None = None,
    include_file_available: bool = False,
) -> SourceResponse:
    """Build a full source API response from a domain source."""
    embedded_chunks = await source.get_embedded_chunks()
    kg_extracted = await source.has_knowledge_graph()
    asset = (
        AssetModel(
            file_path=source.asset.file_path if source.asset else None,
            url=source.asset.url if source.asset else None,
        )
        if source.asset
        else None
    )

    return SourceResponse(
        id=source.id or "",
        title=source.title,
        topics=source.topics or [],
        asset=asset,
        full_text=source.full_text,
        embedded=embedded_chunks > 0,
        embedded_chunks=embedded_chunks,
        kg_extracted=kg_extracted,
        file_available=is_source_file_available(source)
        if include_file_available
        else None,
        created=str(source.created),
        updated=str(source.updated),
        command_id=command_id
        if command_id is not None
        else str(source.command)
        if source.command
        else None,
        status=status,
        processing_info=processing_info,
        notebooks=notebooks,
        owner_id=source.owner_id,
        workspace_id=str(source.workspace_id) if source.workspace_id else None,
        visibility=source.visibility,
    )


async def notebook_ids_for_source(source_id: str) -> list[str]:
    return await SourceRepository.referenced_notebook_ids(source_id)


async def assign_processing_command(source: Source, command_id: str) -> None:
    """Persist a source -> command link, marking the command failed if persistence fails."""
    source.command = ensure_record_id(command_id)
    try:
        await source.save()
    except Exception as exc:
        logger.exception(
            f"Failed to persist command {command_id} on source {source.id}; marking command failed"
        )
        try:
            await mark_command_failed(
                command_id,
                f"Failed to attach command to source {source.id}: {exc}",
            )
        except Exception:
            logger.exception(f"Failed to mark orphan command {command_id} as failed")
        raise


async def create_source_and_queue_processing(
    source_data: SourceCreate,
    *,
    user_id: str | None,
    file_path: str | None = None,
) -> SourceResponse:
    """Create a source record and queue background processing."""
    content_state = build_source_content_state(source_data, file_path=file_path)
    team_id = await resolve_source_team_context(source_data.notebooks)
    transformation_ids = await validate_source_create_request(
        source_data,
        team_id=team_id,
    )

    source = Source(
        title=source_data.title or "Processing...",
        topics=[],
        asset=build_source_asset(source_data, file_path=file_path),
        owner_id=user_id,
        workspace_id=await resolve_source_workspace_id(
            source_data,
            user_id=user_id,
        ),
        visibility=source_data.visibility,
    )
    await source.save()

    for notebook_id in source_data.notebooks or []:
        await source.add_to_notebook(notebook_id)

    try:
        command_input = SourceProcessingInput(
            source_id=str(source.id),
            content_state=content_state,
            notebook_ids=source_data.notebooks,
            transformations=transformation_ids,
            embed=source_data.embed,
            team_id=team_id,
        )
        command_id = await submit_process_source_command(command_input.model_dump())
    except Exception:
        logger.exception("Failed to submit source processing command")
        try:
            await source.delete()
        except Exception:
            logger.exception("Failed to clean up source after command submission error")
        raise

    await assign_processing_command(source, command_id)

    return source_response_for_queued_processing(
        source,
        command_id=command_id,
        notebooks=source_data.notebooks,
    )


async def get_source_response(source_id: str, *, user_id: str | None) -> SourceResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not await can_read_resource(
        resource_type="source",
        resource_id=source.id or source_id,
        user_id=user_id,
        owner_id=str(source.owner_id) if source.owner_id else None,
        visibility=source.visibility,
    ):
        raise PermissionError("Access denied")

    status = None
    processing_info = None
    if source.command:
        try:
            status = await source.get_status()
            processing_info = await source.get_processing_progress()
        except Exception as e:
            logger.warning(f"Failed to get status for source {source_id}: {e}")
            status = "unknown"

    notebooks = await notebook_ids_for_source(source.id or source_id)
    return await source_response_from_source(
        source,
        notebooks=notebooks,
        status=status,
        processing_info=processing_info,
        include_file_available=True,
    )


def source_status_message(status: str | None) -> str:
    if status == "completed":
        return "Source processing completed successfully"
    if status == "failed":
        return "Source processing failed"
    if status == "running":
        return "Source processing in progress"
    if status == "queued":
        return "Source processing queued"
    if status == "unknown":
        return "Source processing status unknown"
    return f"Source processing status: {status}"


async def get_source_status_response(
    source_id: str,
    *,
    user_id: str | None,
    timeout_seconds: int,
) -> SourceStatusResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not await can_read_resource(
        resource_type="source",
        resource_id=source.id or source_id,
        user_id=user_id,
        owner_id=str(source.owner_id) if source.owner_id else None,
        visibility=source.visibility,
    ):
        raise PermissionError("Access denied")

    if not source.command:
        return SourceStatusResponse(
            status=None,
            message="Legacy source (completed before async processing)",
            processing_info=None,
            command_id=None,
        )

    command_id = str(source.command)
    try:
        status_result = await get_command_status(command_id)
        if not status_result:
            return SourceStatusResponse(
                status="unknown",
                message="Source processing status unknown",
                processing_info=None,
                command_id=command_id,
            )

        status = command_lifecycle.command_status_value(status_result.status)
        result = getattr(status_result, "result", None)
        execution_metadata = (
            result.get("execution_metadata", {}) if isinstance(result, dict) else {}
        )
        error_message = getattr(status_result, "error_message", None)

        if status in command_lifecycle.ACTIVE_COMMAND_STATUSES and (
            command_lifecycle.is_command_timed_out(
                getattr(status_result, "created", None),
                timeout_seconds=timeout_seconds,
            )
        ):
            await mark_command_failed(command_id, SOURCE_PROCESSING_TIMEOUT_MESSAGE)
            status = "failed"
            error_message = SOURCE_PROCESSING_TIMEOUT_MESSAGE
            if not isinstance(result, dict):
                result = {}
            result = {**result, "success": False, "error_message": error_message}

        processing_info = {
            "status": status,
            "started_at": execution_metadata.get("started_at"),
            "completed_at": execution_metadata.get("completed_at"),
            "error": error_message,
            "result": result,
        }

        return SourceStatusResponse(
            status=status,
            message=source_status_message(status),
            processing_info=processing_info,
            command_id=command_id,
        )
    except Exception as e:
        logger.warning(f"Failed to get status for source {source_id}: {e}")
        return SourceStatusResponse(
            status="unknown",
            message="Failed to retrieve processing status",
            processing_info=None,
            command_id=command_id,
        )


async def update_source_details(
    source_id: str,
    source_update: SourceUpdate,
    *,
    user_id: str | None,
) -> SourceResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not check_source_ownership(source.owner_id, user_id):
        raise PermissionError("Access denied")

    if source_update.title is not None:
        source.title = source_update.title
    if source_update.topics is not None:
        source.topics = source_update.topics
    if source_update.visibility is not None:
        source.visibility = source_update.visibility

    await source.save()
    return await source_response_from_source(source)


async def update_source_visibility_use_case(
    source_id: str,
    *,
    user_id: str | None,
) -> SourceListResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not check_source_ownership(source.owner_id, user_id):
        raise PermissionError("Access denied - you do not own this source")

    if source.visibility == "public":
        raise InvalidInputError(
            "Source is already public. Making a source private is not supported."
        )

    source.visibility = "public"
    await source.save()

    row = await SourceRepository.get_list_row(source_id)
    if not row:
        raise NotFoundError("Source not found after update")

    return source_list_response_from_row(row)


def retry_content_state_for_source(source: Source) -> dict[str, Any]:
    if source.asset:
        if source.asset.file_path:
            return {"file_path": source.asset.file_path, "delete_source": False}
        if source.asset.url:
            return {"url": source.asset.url}
        raise InvalidInputError("Source asset has no file_path or url")

    if source.full_text:
        return {"content": source.full_text}

    raise InvalidInputError("Cannot determine source content for retry")


async def retry_source_processing_use_case(
    source_id: str,
    *,
    user_id: str | None,
) -> SourceResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not check_source_ownership(source.owner_id, user_id):
        raise PermissionError("Access denied")

    if source.command:
        try:
            status = await source.get_status()
            if status in ["running", "queued"]:
                raise InvalidInputError(
                    "Source is already processing. Cannot retry while processing is active."
                )
        except InvalidInputError:
            raise
        except Exception as e:
            logger.warning(
                f"Failed to check current status for source {source_id}: {e}"
            )

    notebook_ids = await notebook_ids_for_source(source.id or source_id)
    if not notebook_ids:
        raise InvalidInputError("Source is not associated with any notebooks")
    team_id = await resolve_resource_team_context(
        resource_type="source",
        resource_id=source.id or source_id,
    )

    command_input = SourceProcessingInput(
        source_id=str(source.id),
        content_state=retry_content_state_for_source(source),
        notebook_ids=notebook_ids,
        transformations=[],
        embed=True,
        team_id=team_id,
    )

    command_id = await submit_process_source_command(command_input.model_dump())
    logger.info(
        f"Submitted retry processing command: {command_id} for source {source_id}"
    )

    await assign_processing_command(source, command_id)

    return await source_response_from_source(
        source,
        command_id=command_id,
        status="queued",
        processing_info={"retry": True, "queued": True},
    )


async def queue_knowledge_graph_extraction(
    source_id: str,
    *,
    user_id: str | None,
) -> dict[str, Any]:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not check_source_ownership(source.owner_id, user_id):
        raise PermissionError("Access denied")

    if not source.full_text or not source.full_text.strip():
        raise InvalidInputError(
            "Source has no text content to extract knowledge graph from"
        )

    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "extract_knowledge_graph",
        {"source_id": source_id},
    )
    logger.info(
        f"Knowledge graph extraction queued for source {source_id}: {command_id}"
    )

    return {
        "success": True,
        "source_id": source_id,
        "command_id": str(command_id),
        "message": "Knowledge graph extraction queued",
    }


async def create_source_insight_use_case(
    source_id: str,
    request: CreateSourceInsightRequest,
    *,
    user_id: str | None,
) -> InsightCreationResponse:
    source = await Source.get(source_id)
    if not source:
        raise NotFoundError("Source not found")

    if not check_source_ownership(source.owner_id, user_id):
        raise PermissionError("Access denied")

    transformation = await Transformation.get(request.transformation_id)
    if not transformation:
        raise NotFoundError("Transformation not found")

    command_id = await CommandService.submit_command_job(
        "open_notebook",
        "run_transformation",
        {
            "source_id": source_id,
            "transformation_id": request.transformation_id,
        },
    )
    logger.info(
        f"Submitted run_transformation command {command_id} for source {source_id}"
    )

    return InsightCreationResponse(
        status="pending",
        message="Insight generation started",
        source_id=source_id,
        transformation_id=request.transformation_id,
        command_id=str(command_id),
    )
