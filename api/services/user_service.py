from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from api.auth import CurrentUser
from api.models import (
    ResetUserPasswordResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserListItem,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from api.password_utils import hash_password
from api.services.workspace_service import ensure_personal_workspace_for_user
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.user_repository import UserRepository
from open_notebook.exceptions import InvalidInputError, NotFoundError


def _default_user_role(row: dict) -> str:
    return row.get("role") or ("admin" if row.get("username") == "admin" else "user")


def _default_user_status(row: dict) -> str:
    return row.get("status") or "active"


def _user_response(row: dict, *, temporary_password: Optional[str] = None) -> UserResponse:
    response_cls = UserCreateResponse if temporary_password is not None else UserResponse
    data = dict(
        id=str(row.get("id", "")),
        username=row.get("username", ""),
        email=row.get("email"),
        display_name=row.get("display_name"),
        role=_default_user_role(row),
        status=_default_user_status(row),
        locale=row.get("locale"),
        theme=row.get("theme"),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
        last_login_at=str(row.get("last_login_at", ""))
        if row.get("last_login_at")
        else None,
    )
    if temporary_password is not None:
        data["temporary_password"] = temporary_password
    return response_cls(**data)


def _user_list_item(row: dict) -> UserListItem:
    return UserListItem(
        id=str(row.get("id", "")),
        username=row.get("username", ""),
        email=row.get("email"),
        display_name=row.get("display_name"),
        role=_default_user_role(row),
        status=_default_user_status(row),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
        last_login_at=str(row.get("last_login_at", ""))
        if row.get("last_login_at")
        else None,
        source_count=int(row.get("source_count", 0) or 0),
        notebook_count=int(row.get("notebook_count", 0) or 0),
    )


async def list_users_use_case(
    *,
    q: Optional[str],
    role: Optional[str],
    status: Optional[str],
    limit: int,
    offset: int,
) -> UserListResponse:
    rows = await UserRepository.list_users(
        q=q, role=role, status=status, limit=limit, offset=offset
    )
    total = await UserRepository.count_users(q=q, role=role, status=status)
    return UserListResponse(
        items=[_user_list_item(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


async def create_user_use_case(
    request: UserCreateRequest,
    *,
    actor: CurrentUser,
) -> UserCreateResponse:
    if await UserRepository.get_user_by_username(request.username):
        raise InvalidInputError("Username already exists")

    password = request.password or secrets.token_urlsafe(12)
    row = await UserRepository.create_user(
        {
            "username": request.username,
            "email": request.email,
            "display_name": request.display_name or request.username,
            "role": request.role,
            "status": "active",
            "hashed_password": hash_password(password),
            "created_by": actor.id,
        }
    )
    if not row:
        raise InvalidInputError("Failed to create user")

    await ensure_personal_workspace_for_user(
        user_id=str(row.get("id", "")),
        display_name=row.get("display_name") or row.get("username"),
    )

    await AuditLogRepository.create(
        action="user.created",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="app_user",
        target_id=str(row.get("id", "")),
        metadata={"role": request.role},
    )
    return _user_response(
        row,
        temporary_password=password if request.password is None else None,
    )


async def get_user_use_case(user_id: str) -> UserResponse:
    row = await UserRepository.get_user(user_id)
    if not row:
        raise NotFoundError("User not found")
    return _user_response(row)


async def update_user_use_case(
    user_id: str,
    request: UserUpdateRequest,
    *,
    actor: CurrentUser,
) -> UserResponse:
    row = await UserRepository.get_user(user_id)
    if not row:
        raise NotFoundError("User not found")

    current_role = _default_user_role(row)
    current_status = _default_user_status(row)
    next_role = request.role or current_role
    next_status = request.status or current_status

    demoting_or_disabling_admin = (
        current_role == "admin" and (next_role != "admin" or next_status != "active")
    )
    if demoting_or_disabling_admin:
        remaining = await UserRepository.count_active_admins(
            self_excluding_user_id=user_id
        )
        if remaining <= 0:
            raise InvalidInputError("Cannot remove the last active admin")

    if actor.id == user_id and next_status != "active":
        raise InvalidInputError("Admins cannot disable their own account")

    updates = {}
    if not row.get("role"):
        updates["role"] = current_role
    if not row.get("status"):
        updates["status"] = current_status
    if request.display_name is not None:
        updates["display_name"] = request.display_name
    if request.role is not None:
        updates["role"] = request.role
    if request.status is not None:
        updates["status"] = request.status
    if not updates:
        return _user_response(row)

    updated = await UserRepository.update_user(user_id, updates)
    await AuditLogRepository.create(
        action="user.updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="app_user",
        target_id=user_id,
        metadata=updates,
    )
    return _user_response(updated[0] if updated else {**row, **updates})


async def reset_user_password_use_case(
    user_id: str,
    *,
    actor: CurrentUser,
) -> ResetUserPasswordResponse:
    row = await UserRepository.get_user(user_id)
    if not row:
        raise NotFoundError("User not found")

    temporary_password = secrets.token_urlsafe(12)
    await UserRepository.update_user(
        user_id,
        {
            "hashed_password": hash_password(temporary_password),
            "password_changed_at": datetime.now(timezone.utc),
        },
    )
    await AuditLogRepository.create(
        action="auth.password.reset",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="app_user",
        target_id=user_id,
    )
    return ResetUserPasswordResponse(
        success=True,
        temporary_password=temporary_password,
        message="Password reset successfully",
    )
