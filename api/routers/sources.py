import os
from datetime import datetime
from typing import Any, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from loguru import logger

from api.models import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkDeleteResult,
    CreateSourceInsightRequest,
    InsightCreationResponse,
    SourceCreate,
    SourceInsightResponse,
    SourceListResponse,
    SourceResponse,
    SourceStatusResponse,
    SourceUpdate,
)
from api.services import command_lifecycle
from api.services.source_forms import parse_source_form_data
from api.services.source_permissions import check_source_access as _check_source_access
from api.services.source_permissions import (
    check_source_ownership as _check_source_ownership,
)
from api.services.source_responses import source_list_response_from_row
from api.services.share_service import can_read_resource
from api.services.source_service import (
    create_source_and_queue_processing,
    create_source_insight_use_case,
    get_source_response,
    get_source_status_response,
    queue_knowledge_graph_extraction,
    retry_source_processing_use_case,
    update_source_details,
    update_source_visibility_use_case,
)
from api.services.source_uploads import save_uploaded_file
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.database.repositories.source_repository import SourceRepository
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter()

SOURCE_PROCESSING_TIMEOUT_SECONDS = int(
    os.environ.get("LUMINA_WORKER_TASK_TIMEOUT_SECONDS", str(20 * 60))
)
_coerce_datetime = command_lifecycle.coerce_datetime
_command_status_value = command_lifecycle.command_status_value


def _is_command_timed_out(created_at: Any, *, now: Optional[datetime] = None) -> bool:
    return command_lifecycle.is_command_timed_out(
        created_at,
        timeout_seconds=SOURCE_PROCESSING_TIMEOUT_SECONDS,
        now=now,
    )


@router.get("/sources", response_model=List[SourceListResponse])
async def get_sources(
    request: Request,
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    title_contains: Optional[str] = Query(
        None, description="Filter sources by title substring"
    ),
    limit: int = Query(
        50, ge=1, le=100, description="Number of sources to return (1-100)"
    ),
    offset: int = Query(0, ge=0, description="Number of sources to skip"),
    sort_by: str = Query(
        "updated", description="Field to sort by (created or updated)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
):
    """Get sources with pagination, sorting, and filtering support.

    Returns sources owned by the user (private + public) plus all public sources.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    team_ids = await TeamRepository.user_team_ids(user_id) if user_id else []
    try:
        # Validate sort parameters
        if sort_by not in ["created", "updated"]:
            raise HTTPException(
                status_code=400, detail="sort_by must be 'created' or 'updated'"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="sort_order must be 'asc' or 'desc'"
            )

        if notebook_id:
            # Verify notebook exists first
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

        result = await SourceRepository.list_sources(
            user_id=user_id,
            team_ids=team_ids,
            notebook_id=notebook_id,
            title_contains=title_contains,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return [source_list_response_from_row(row) for row in result]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sources: {str(e)}")


@router.get("/sources/public", response_model=List[SourceListResponse])
async def get_public_sources(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    title_contains: Optional[str] = Query(
        None, description="Filter sources by title substring"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("updated"),
    sort_order: str = Query("desc"),
):
    """Browse public sources without authentication."""
    try:
        if sort_by not in ["created", "updated"]:
            raise HTTPException(
                status_code=400, detail="sort_by must be 'created' or 'updated'"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="sort_order must be 'asc' or 'desc'"
            )

        if notebook_id:
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

        result = await SourceRepository.list_sources(
            user_id=None,
            notebook_id=notebook_id,
            title_contains=title_contains,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            public_only=True,
        )

        return [source_list_response_from_row(row) for row in result]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public sources: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching public sources: {str(e)}"
        )


@router.post("/sources", response_model=SourceResponse)
async def create_source(
    request: Request,
    form_data: tuple[SourceCreate, Optional[UploadFile]] = Depends(
        parse_source_form_data
    ),
):
    """Create a new source and queue background processing."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    source_data, upload_file = form_data
    file_path: str | None = None

    try:
        if upload_file and source_data.type == "upload":
            try:
                file_path = await save_uploaded_file(upload_file)
            except Exception as e:
                logger.error(f"File upload failed: {e}")
                raise HTTPException(
                    status_code=400, detail=f"File upload failed: {str(e)}"
                )

        return await create_source_and_queue_processing(
            source_data,
            user_id=user_id,
            file_path=file_path,
        )

    except HTTPException:
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise
    except NotFoundError as e:
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        # Clean up uploaded file on unexpected errors if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Error creating source: {str(e)}")


async def _resolve_source_file(source_id: str) -> tuple[str, str]:
    source = await Source.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    file_path = source.asset.file_path if source.asset else None
    if not file_path:
        raise HTTPException(status_code=404, detail="Source has no file to download")

    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        logger.warning(
            f"Blocked download outside uploads directory for source {source_id}: {resolved_path}"
        )
        raise HTTPException(status_code=403, detail="Access to file denied")

    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    filename = os.path.basename(resolved_path)
    return resolved_path, filename


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(request: Request, source_id: str):
    """Get a specific source by ID. Requires ownership (private) or public."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        return await get_source_response(source_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching source: {str(e)}")


@router.head("/sources/{source_id}/download")
async def check_source_file(request: Request, source_id: str):
    """Check if a source has a downloadable file. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not await can_read_resource(
            resource_type="source",
            resource_id=source.id or source_id,
            user_id=user_id,
            owner_id=str(source.owner_id) if source.owner_id else None,
            visibility=source.visibility,
        ):
            raise HTTPException(status_code=403, detail="Access denied")
        await _resolve_source_file(source_id)
        return Response(status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify file")


@router.patch("/sources/{source_id}/visibility")
async def update_source_visibility(request: Request, source_id: str):
    """Make a private source public. One-way only — cannot revert to private.

    Requires ownership. Returns the updated source.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return await update_source_visibility_use_case(source_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating visibility for source {source_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error updating visibility: {str(e)}"
        )


@router.get("/sources/{source_id}/download")
async def download_source_file(request: Request, source_id: str):
    """Download the original file associated with an uploaded source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not await can_read_resource(
            resource_type="source",
            resource_id=source.id or source_id,
            user_id=user_id,
            owner_id=str(source.owner_id) if source.owner_id else None,
            visibility=source.visibility,
        ):
            raise HTTPException(status_code=403, detail="Access denied")
        resolved_path, filename = await _resolve_source_file(source_id)
        return FileResponse(
            path=resolved_path,
            filename=filename,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download source file")


@router.get("/sources/{source_id}/status", response_model=SourceStatusResponse)
async def get_source_status(request: Request, source_id: str):
    """Get processing status for a source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        return await get_source_status_response(
            source_id,
            user_id=user_id,
            timeout_seconds=SOURCE_PROCESSING_TIMEOUT_SECONDS,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching status for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching source status: {str(e)}"
        )


@router.put("/sources/{source_id}", response_model=SourceResponse)
async def update_source(request: Request, source_id: str, source_update: SourceUpdate):
    """Update a source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        return await update_source_details(
            source_id,
            source_update,
            user_id=user_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating source: {str(e)}")


@router.post("/sources/{source_id}/retry", response_model=SourceResponse)
async def retry_source_processing(request: Request, source_id: str):
    """Retry processing for a failed or stuck source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        return await retry_source_processing_use_case(source_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrying source processing for {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrying source processing: {str(e)}"
        )


@router.delete("/sources/{source_id}")
async def delete_source(request: Request, source_id: str):
    """Delete a source. Requires ownership.

    Public sources that are referenced by notebooks cannot be deleted.
    Remove the source from all notebooks first.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Ownership check
        if not _check_source_ownership(source.owner_id, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        await source.delete()

        return {"message": "Source deleted successfully"}
    except InvalidInputError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting source: {str(e)}")


@router.post("/sources/{source_id}/extract-kg")
async def extract_knowledge_graph(request: Request, source_id: str):
    """Trigger knowledge graph extraction for a source. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        return await queue_knowledge_graph_extraction(source_id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering KG extraction for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error triggering KG extraction: {str(e)}"
        )


@router.post("/sources/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_sources(request: Request, body: BulkDeleteRequest):
    """Delete multiple sources at once. Only deletes sources the user owns.

    Public sources that are referenced by notebooks will be skipped
    with an error in the per-source results.

    Returns a per-source breakdown of which were deleted and which failed (with reasons).
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    results: list[BulkDeleteResult] = []
    deleted_count = 0
    failed_count = 0

    for source_id in body.source_ids:
        try:
            source = await Source.get(source_id)
            if not source:
                results.append(
                    BulkDeleteResult(
                        source_id=source_id,
                        title="(not found)",
                        deleted=False,
                        error="Source not found",
                    )
                )
                failed_count += 1
                continue

            title = source.title or "(untitled)"

            if not _check_source_ownership(source.owner_id, user_id):
                results.append(
                    BulkDeleteResult(
                        source_id=source_id,
                        title=title,
                        deleted=False,
                        error="Access denied — you do not own this source",
                    )
                )
                failed_count += 1
                continue

            await source.delete()
            results.append(
                BulkDeleteResult(source_id=source_id, title=title, deleted=True)
            )
            deleted_count += 1

        except InvalidInputError as e:
            results.append(
                BulkDeleteResult(
                    source_id=source_id, title=title, deleted=False, error=str(e)
                )
            )
            failed_count += 1
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in bulk delete for source {source_id}: {e}")
            results.append(
                BulkDeleteResult(
                    source_id=source_id, title="(error)", deleted=False, error=str(e)
                )
            )
            failed_count += 1

    return BulkDeleteResponse(
        total_requested=len(body.source_ids),
        deleted_count=deleted_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/sources/{source_id}/insights", response_model=List[SourceInsightResponse])
async def get_source_insights(request: Request, source_id: str):
    """Get all insights for a specific source. Requires access."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Access check
        if not await can_read_resource(
            resource_type="source",
            resource_id=source.id or source_id,
            user_id=user_id,
            owner_id=str(source.owner_id) if source.owner_id else None,
            visibility=source.visibility,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        insights = await source.get_insights()
        return [
            SourceInsightResponse(
                id=insight.id or "",
                source_id=source_id,
                insight_type=insight.insight_type,
                content=insight.content,
                created=str(insight.created),
                updated=str(insight.updated),
            )
            for insight in insights
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insights for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching insights: {str(e)}"
        )


@router.post(
    "/sources/{source_id}/insights",
    response_model=InsightCreationResponse,
    status_code=202,
)
async def create_source_insight(
    http_request: Request, source_id: str, request: CreateSourceInsightRequest
):
    """Start insight generation for a source by running a transformation. Requires ownership."""
    user_id: Optional[str] = getattr(http_request.state, "user_id", None)
    try:
        return await create_source_insight_use_case(
            source_id,
            request,
            user_id=user_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting insight generation for source {source_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting insight generation: {str(e)}"
        )
