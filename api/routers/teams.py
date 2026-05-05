from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import CurrentUser, get_current_user, require_admin
from api.models import (
    DeleteResponse,
    TeamCreateRequest,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberUpsertRequest,
    TeamResponse,
    TeamUpdateRequest,
)
from api.services.team_service import (
    create_team_use_case,
    delete_team_use_case,
    list_teams_use_case,
    list_members_use_case,
    remove_member_use_case,
    update_team_use_case,
    upsert_member_use_case,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=TeamListResponse)
async def list_teams(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: CurrentUser = Depends(get_current_user),
):
    return await list_teams_use_case(actor=actor, q=q, limit=limit, offset=offset)


@router.post("", response_model=TeamResponse)
async def create_team(
    request: TeamCreateRequest,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await create_team_use_case(request, actor=actor)
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    teams = await list_teams_use_case(actor=actor, q=None, limit=200, offset=0)
    for team in teams.items:
        if team.id == team_id:
            return team
    raise HTTPException(status_code=404, detail="Team not found")


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    request: TeamUpdateRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await update_team_use_case(team_id, request, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}", response_model=DeleteResponse)
async def delete_team(
    team_id: str,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await delete_team_use_case(team_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: str,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await list_members_use_case(
            team_id, actor=actor, limit=limit, offset=offset
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def upsert_member(
    team_id: str,
    request: TeamMemberUpsertRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await upsert_member_use_case(team_id, request, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{user_id}", response_model=DeleteResponse)
async def remove_member(
    team_id: str,
    user_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await remove_member_use_case(team_id, user_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
