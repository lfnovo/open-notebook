from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import CurrentUser, get_current_user
from api.models import DeleteResponse, ShareGrantCreateRequest, ShareGrantResponse
from api.services.share_service import (
    create_share_grant_use_case,
    delete_share_grant_use_case,
    list_resource_grants_use_case,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter(prefix="/share-grants", tags=["share-grants"])


@router.get("", response_model=list[ShareGrantResponse])
async def list_share_grants(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await list_resource_grants_use_case(
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=ShareGrantResponse)
async def create_share_grant(
    request: ShareGrantCreateRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await create_share_grant_use_case(request, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{grant_id}", response_model=DeleteResponse)
async def delete_share_grant(
    grant_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await delete_share_grant_use_case(grant_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=409, detail=str(e))
