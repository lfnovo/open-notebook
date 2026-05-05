from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import CurrentUser, require_admin
from api.models import (
    ResetUserPasswordResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from api.services.user_service import (
    create_user_use_case,
    get_user_use_case,
    list_users_use_case,
    reset_user_password_use_case,
    update_user_use_case,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_admin),
):
    return await list_users_use_case(
        q=q, role=role, status=status, limit=limit, offset=offset
    )


@router.post("", response_model=UserCreateResponse)
async def create_user(
    request: UserCreateRequest,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await create_user_use_case(request, actor=actor)
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, _: CurrentUser = Depends(require_admin)):
    try:
        return await get_user_use_case(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await update_user_use_case(user_id, request, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{user_id}/reset-password", response_model=ResetUserPasswordResponse)
async def reset_user_password(
    user_id: str,
    actor: CurrentUser = Depends(require_admin),
):
    try:
        return await reset_user_password_use_case(user_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
