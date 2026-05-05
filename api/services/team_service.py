from __future__ import annotations

import re
from typing import Optional

from api.auth import CurrentUser
from api.models import (
    DeleteResponse,
    TeamCreateRequest,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberUpsertRequest,
    TeamMemberUser,
    TeamResponse,
    TeamUpdateRequest,
)
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.user_repository import UserRepository
from open_notebook.exceptions import InvalidInputError, NotFoundError


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "team"


def _team_response(row: dict) -> TeamResponse:
    return TeamResponse(
        id=str(row.get("id", "")),
        slug=row.get("slug", ""),
        name=row.get("name", ""),
        type=row.get("type", "workspace"),
        created_by=str(row.get("created_by", "")) if row.get("created_by") else None,
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
        member_count=int(row.get("member_count", 0) or 0),
        share_count=int(row.get("share_count", 0) or 0),
    )


def _member_response(row: dict) -> TeamMemberResponse:
    user = row.get("user")
    user_info = None
    if isinstance(user, dict):
        user_info = TeamMemberUser(
            id=str(user.get("id", "")),
            username=user.get("username", ""),
            display_name=user.get("display_name"),
            email=user.get("email"),
        )
    return TeamMemberResponse(
        id=str(row.get("id", "")),
        team=str(row.get("team", "")),
        user=str(user.get("id")) if isinstance(user, dict) else str(row.get("user", "")),
        user_info=user_info,
        role=row.get("role", "member"),
        status=row.get("status", "active"),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")) if row.get("updated") else None,
    )


async def _ensure_team_manager(team_id: str, actor: CurrentUser) -> None:
    if actor.role == "admin":
        return
    member = await TeamRepository.get_member(team_id, actor.id)
    if not member or member.get("status") != "active" or member.get("role") not in {
        "owner",
        "admin",
    }:
        raise PermissionError("Team owner or admin privileges required")


async def list_teams_use_case(
    *,
    actor: CurrentUser,
    q: Optional[str],
    limit: int,
    offset: int,
) -> TeamListResponse:
    rows = await TeamRepository.list_teams(
        user_id=actor.id,
        include_all_for_admin=actor.role == "admin",
        q=q,
        limit=limit,
        offset=offset,
    )
    return TeamListResponse(
        items=[_team_response(row) for row in rows],
        total=len(rows),
        limit=limit,
        offset=offset,
    )


async def create_team_use_case(
    request: TeamCreateRequest,
    *,
    actor: CurrentUser,
) -> TeamResponse:
    slug = _slugify(request.slug or request.name)
    if slug == "public":
        raise InvalidInputError("'public' is a reserved team slug")
    if await TeamRepository.get_team_by_slug(slug):
        raise InvalidInputError("Team slug already exists")

    row = await TeamRepository.create_team(
        {"slug": slug, "name": request.name, "created_by": actor.id}
    )
    if not row:
        raise InvalidInputError("Failed to create team")
    await TeamRepository.create_member(
        team_id=str(row["id"]),
        user_id=actor.id,
        role="owner",
        status="active",
    )
    await AuditLogRepository.create(
        action="team.created",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=str(row.get("id", "")),
        metadata={"slug": slug},
    )
    row["member_count"] = 1
    return _team_response(row)


async def update_team_use_case(
    team_id: str,
    request: TeamUpdateRequest,
    *,
    actor: CurrentUser,
) -> TeamResponse:
    row = await TeamRepository.get_team(team_id)
    if not row:
        raise NotFoundError("Team not found")
    if row.get("type") == "system":
        raise InvalidInputError("System teams cannot be modified")
    await _ensure_team_manager(team_id, actor)

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if updates:
        updated = await TeamRepository.update_team(team_id, updates)
        row = updated[0] if updated else {**row, **updates}
        await AuditLogRepository.create(
            action="team.updated",
            actor_id=actor.id,
            actor_username=actor.username,
            target_type="team",
            target_id=team_id,
            metadata=updates,
        )
    return _team_response(row)


async def delete_team_use_case(team_id: str, *, actor: CurrentUser) -> DeleteResponse:
    row = await TeamRepository.get_team(team_id)
    if not row:
        raise NotFoundError("Team not found")
    if row.get("type") == "system":
        raise InvalidInputError("System teams cannot be deleted")
    if actor.role != "admin":
        raise PermissionError("Admin privileges required")
    deps = await TeamRepository.dependency_counts(team_id)
    if deps.get("active_members", 0) > 0 or deps.get("share_grants", 0) > 0:
        raise InvalidInputError(
            "Team cannot be deleted while it has active members or share grants"
        )
    await TeamRepository.delete_team(team_id)
    await AuditLogRepository.create(
        action="team.deleted",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata=deps,
    )
    return DeleteResponse(success=True, message="Team deleted")


async def list_members_use_case(
    team_id: str,
    *,
    actor: CurrentUser,
    limit: int,
    offset: int,
) -> list[TeamMemberResponse]:
    await _ensure_team_manager(team_id, actor)
    rows = await TeamRepository.list_members(team_id=team_id, limit=limit, offset=offset)
    return [_member_response(row) for row in rows]


async def upsert_member_use_case(
    team_id: str,
    request: TeamMemberUpsertRequest,
    *,
    actor: CurrentUser,
) -> TeamMemberResponse:
    team = await TeamRepository.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")
    if team.get("type") == "system":
        raise InvalidInputError("System team members cannot be managed")
    await _ensure_team_manager(team_id, actor)

    user = await UserRepository.get_user(request.user_id)
    if not user:
        raise NotFoundError("User not found")
    if user.get("status", "active") != "active":
        raise InvalidInputError("Only active users can be added to a team")

    existing = await TeamRepository.get_member(team_id, request.user_id)
    if existing and existing.get("role") == "owner" and request.role != "owner":
        remaining = await TeamRepository.count_active_owners(
            team_id, excluding_user_id=request.user_id
        )
        if remaining <= 0:
            raise InvalidInputError("Team must keep at least one active owner")

    if existing:
        row = await TeamRepository.update_member(
            team_id=team_id,
            user_id=request.user_id,
            role=request.role,
            status=request.status,
        )
        action = "team.member_updated"
    else:
        row = await TeamRepository.create_member(
            team_id=team_id,
            user_id=request.user_id,
            role=request.role,
            status=request.status,
        )
        action = "team.member_added"

    await AuditLogRepository.create(
        action=action,
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata={"user_id": request.user_id, "role": request.role},
    )
    return _member_response(row or {})


async def remove_member_use_case(
    team_id: str,
    user_id: str,
    *,
    actor: CurrentUser,
) -> DeleteResponse:
    team = await TeamRepository.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")
    if team.get("type") == "system":
        raise InvalidInputError("System team members cannot be managed")
    await _ensure_team_manager(team_id, actor)

    existing = await TeamRepository.get_member(team_id, user_id)
    if not existing:
        raise NotFoundError("Team member not found")
    if existing.get("role") == "owner":
        remaining = await TeamRepository.count_active_owners(
            team_id, excluding_user_id=user_id
        )
        if remaining <= 0 and actor.role != "admin":
            raise InvalidInputError("Team must keep at least one active owner")

    await TeamRepository.remove_member(team_id, user_id)
    await AuditLogRepository.create(
        action="team.member_removed",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata={"user_id": user_id},
    )
    return DeleteResponse(success=True, message="Team member removed")
