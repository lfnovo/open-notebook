from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import CurrentUser, get_current_user, require_admin
from api.models import (
    ExternalApiCommandResponse,
    ExternalApiConnectionCreate,
    ExternalApiConnectionListResponse,
    ExternalApiConnectionResponse,
    ExternalApiConnectionTestResponse,
    ExternalApiFetchRequest,
    ExternalApiSearchRequest,
    ExternalApiUsageResponse,
    ExternalAvailableSourceListResponse,
    ExternalItemNotebookReferenceRequest,
    ExternalItemSnapshotRequest,
    ExternalItemSnapshotResponse,
    ExternalOutputGenerateRequest,
    ExternalSourceCreate,
    ExternalSourceItemResponse,
    ExternalSourceListResponse,
    ExternalSourceResponse,
    ExternalSourceTeamGrantCreate,
    ExternalSourceTeamGrantListResponse,
    ExternalSourceTeamGrantResponse,
    ExternalSourceTeamGrantUpdate,
)
from api.services import external_api_service
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
    RateLimitError,
)

router = APIRouter(prefix="/external-api", tags=["external-api"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, RateLimitError):
        raise HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, InvalidInputError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise HTTPException(status_code=500, detail=str(exc))


@router.post("/connections", response_model=ExternalApiConnectionResponse)
async def create_connection(
    request: ExternalApiConnectionCreate,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.create_connection_use_case(request, actor=actor)
    except Exception as exc:
        _raise_http(exc)


@router.get("/connections", response_model=ExternalApiConnectionListResponse)
async def list_connections(
    actor: CurrentUser = Depends(require_admin),
):
    return await external_api_service.list_connections_use_case()


@router.post(
    "/connections/{connection_id}/test",
    response_model=ExternalApiConnectionTestResponse,
)
async def test_connection(
    connection_id: str,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.test_connection_use_case(connection_id)
    except Exception as exc:
        _raise_http(exc)


@router.post("/sources", response_model=ExternalSourceResponse)
async def create_source(
    request: ExternalSourceCreate,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.create_source_use_case(request, actor=actor)
    except Exception as exc:
        _raise_http(exc)


@router.get("/sources", response_model=ExternalSourceListResponse)
async def list_sources(
    actor: CurrentUser = Depends(require_admin),
):
    return await external_api_service.list_sources_use_case()


@router.post(
    "/sources/{source_id}/team-grants",
    response_model=ExternalSourceTeamGrantResponse,
)
async def create_team_grant(
    source_id: str,
    request: ExternalSourceTeamGrantCreate,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.create_team_grant_use_case(
            source_id,
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.get(
    "/sources/{source_id}/team-grants",
    response_model=ExternalSourceTeamGrantListResponse,
)
async def list_team_grants(
    source_id: str,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.list_team_grants_use_case(source_id)
    except Exception as exc:
        _raise_http(exc)


@router.put(
    "/team-grants/{grant_id}",
    response_model=ExternalSourceTeamGrantResponse,
)
async def update_team_grant(
    grant_id: str,
    request: ExternalSourceTeamGrantUpdate,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await external_api_service.update_team_grant_use_case(grant_id, request)
    except Exception as exc:
        _raise_http(exc)


@router.get(
    "/available-sources",
    response_model=ExternalAvailableSourceListResponse,
)
async def list_available_sources(
    team_id: str = Query(...),
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.list_available_sources_use_case(
            team_id=team_id,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.post("/sources/{source_id}/search", response_model=ExternalApiCommandResponse)
async def submit_search(
    source_id: str,
    request: ExternalApiSearchRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.submit_search_use_case(
            source_id,
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.post("/items/{item_id}/fetch", response_model=ExternalApiCommandResponse)
async def submit_fetch(
    item_id: str,
    request: ExternalApiFetchRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.submit_fetch_use_case(
            item_id,
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.post(
    "/items/{item_id}/notebook-references",
    response_model=ExternalSourceItemResponse,
)
async def reference_item(
    item_id: str,
    request: ExternalItemNotebookReferenceRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.reference_item_use_case(
            item_id,
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.post("/items/{item_id}/snapshot", response_model=ExternalItemSnapshotResponse)
async def snapshot_item(
    item_id: str,
    request: ExternalItemSnapshotRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.snapshot_item_use_case(
            item_id,
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.post("/outputs/generate", response_model=ExternalApiCommandResponse)
async def generate_output(
    request: ExternalOutputGenerateRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.submit_output_generate_use_case(
            request,
            actor=actor,
        )
    except Exception as exc:
        _raise_http(exc)


@router.get("/commands/{command_id}")
async def command_status(
    command_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    return await external_api_service.command_status_use_case(command_id)


@router.get("/usage", response_model=ExternalApiUsageResponse)
async def usage(
    team_id: str = Query(...),
    month: Optional[str] = Query(None),
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await external_api_service.usage_use_case(
            team_id=team_id,
            actor=actor,
            month=month,
        )
    except Exception as exc:
        _raise_http(exc)
