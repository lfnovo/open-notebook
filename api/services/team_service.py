from __future__ import annotations

import re
from typing import Optional

from api.auth import CurrentUser
from api.models import (
    DeleteResponse,
    ModelResponse,
    TeamAssignableUserListResponse,
    TeamCreateRequest,
    TeamListResponse,
    TeamMemberResponse,
    TeamMemberUpsertRequest,
    TeamMemberUser,
    TeamModelAllowlistResponse,
    TeamModelAllowlistUpdateRequest,
    TeamModelDefaultsResponse,
    TeamModelDefaultsUpdateRequest,
    TeamResponse,
    TeamTransformationAllowlistResponse,
    TeamTransformationAllowlistUpdateRequest,
    TeamUpdateRequest,
    TransformationResponse,
)
from api.services.workspace_service import ensure_team_workspace_for_team
from open_notebook.ai.models import Model
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.team_allowlist_repository import (
    TeamAllowlistRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.user_repository import UserRepository
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError, NotFoundError


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "team"


def _team_response(row: dict, *, actor: Optional[CurrentUser] = None) -> TeamResponse:
    current_user_role = row.get("current_user_role")
    can_manage = current_user_role in {"owner", "admin"}
    if actor and actor.role == "admin" and row.get("type") != "system":
        can_manage = True

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
        current_user_role=current_user_role,
        can_manage=can_manage,
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


def _team_member_user(row: dict) -> TeamMemberUser:
    return TeamMemberUser(
        id=str(row.get("id", "")),
        username=row.get("username", ""),
        display_name=row.get("display_name"),
        email=row.get("email"),
    )


def _model_response(row: dict) -> ModelResponse:
    return ModelResponse(
        id=str(row.get("id", "")),
        name=row.get("name", ""),
        provider=row.get("provider", ""),
        type=row.get("type", ""),
        credential=str(row.get("credential")) if row.get("credential") else None,
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _transformation_response(row: dict) -> TransformationResponse:
    return TransformationResponse(
        id=str(row.get("id", "")),
        name=row.get("name", ""),
        title=row.get("title", ""),
        description=row.get("description", ""),
        prompt=row.get("prompt", ""),
        apply_default=bool(row.get("apply_default", False)),
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
    )


def _team_model_allowlist_response(
    team_id: str, rows: list[dict]
) -> TeamModelAllowlistResponse:
    models = [
        _model_response(row["model"])
        for row in rows
        if isinstance(row.get("model"), dict)
    ]
    return TeamModelAllowlistResponse(
        team_id=team_id,
        model_ids=[model.id for model in models],
        models=models,
    )


def _team_model_defaults_response(
    team_id: str, row: dict | None
) -> TeamModelDefaultsResponse:
    row = row or {}
    return TeamModelDefaultsResponse(
        team_id=team_id,
        default_chat_model=str(row.get("default_chat_model"))
        if row.get("default_chat_model")
        else None,
        default_embedding_model=str(row.get("default_embedding_model"))
        if row.get("default_embedding_model")
        else None,
        default_transformation_model=str(row.get("default_transformation_model"))
        if row.get("default_transformation_model")
        else None,
        default_tools_model=str(row.get("default_tools_model"))
        if row.get("default_tools_model")
        else None,
        large_context_model=str(row.get("large_context_model"))
        if row.get("large_context_model")
        else None,
    )


def _team_transformation_allowlist_response(
    team_id: str, rows: list[dict]
) -> TeamTransformationAllowlistResponse:
    transformations = [
        _transformation_response(row["transformation"])
        for row in rows
        if isinstance(row.get("transformation"), dict)
    ]
    return TeamTransformationAllowlistResponse(
        team_id=team_id,
        transformation_ids=[item.id for item in transformations],
        transformations=transformations,
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


async def _ensure_workspace_team_for_allowlist(
    team_id: str, actor: CurrentUser
) -> dict:
    team = await TeamRepository.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")
    if team.get("type") == "system":
        raise InvalidInputError("System teams cannot have managed allowlists")
    await _ensure_team_manager(team_id, actor)
    return team


async def _ensure_workspace_team_for_admin_allowlist(
    team_id: str, actor: CurrentUser
) -> dict:
    team = await TeamRepository.get_team(team_id)
    if not team:
        raise NotFoundError("Team not found")
    if team.get("type") == "system":
        raise InvalidInputError("System teams cannot have managed allowlists")
    if actor.role != "admin":
        raise PermissionError("Admin privileges required")
    return team


def _allowed_team_models(rows: list[dict]) -> dict[str, dict]:
    return {
        str(row["model"]["id"]): row["model"]
        for row in rows
        if isinstance(row.get("model"), dict) and row["model"].get("id")
    }


def _validate_team_model_defaults(
    request: TeamModelDefaultsUpdateRequest,
    allowed_models: dict[str, dict],
) -> dict[str, Optional[str]]:
    slot_types = {
        "default_chat_model": "language",
        "default_embedding_model": "embedding",
        "default_transformation_model": "language",
        "default_tools_model": "language",
        "large_context_model": "language",
    }
    updates: dict[str, Optional[str]] = {}
    for field, expected_type in slot_types.items():
        if field not in request.model_fields_set:
            continue
        value = getattr(request, field)
        updates[field] = value
        if not value:
            continue
        model = allowed_models.get(value)
        if not model:
            raise InvalidInputError("Model must be allowed for this team")
        if model.get("type") != expected_type:
            model_label = "embedding model" if expected_type == "embedding" else "language model"
            raise InvalidInputError(f"{field} must use a {model_label}")
    return updates


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
        items=[_team_response(row, actor=actor) for row in rows],
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
    owner = await UserRepository.get_user(request.owner_id)
    if not owner:
        raise NotFoundError("Owner user not found")
    if owner.get("status", "active") != "active":
        raise InvalidInputError("Owner user must be active")
    if await TeamRepository.get_team_by_slug(slug):
        raise InvalidInputError("Team slug already exists")

    row = await TeamRepository.create_team(
        {"slug": slug, "name": request.name, "created_by": actor.id}
    )
    if not row:
        raise InvalidInputError("Failed to create team")
    await TeamRepository.create_member(
        team_id=str(row["id"]),
        user_id=request.owner_id,
        role="owner",
        status="active",
    )
    await ensure_team_workspace_for_team(
        team_id=str(row["id"]),
        name=row.get("name", request.name),
        created_by=actor.id,
    )
    await AuditLogRepository.create(
        action="team.created",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=str(row.get("id", "")),
        metadata={"slug": slug, "owner_id": request.owner_id},
    )
    row["member_count"] = 1
    row["current_user_role"] = "owner" if request.owner_id == actor.id else None
    return _team_response(row, actor=actor)


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
    return _team_response(row, actor=actor)


async def delete_team_use_case(team_id: str, *, actor: CurrentUser) -> DeleteResponse:
    row = await TeamRepository.get_team(team_id)
    if not row:
        raise NotFoundError("Team not found")
    if row.get("type") == "system":
        raise InvalidInputError("System teams cannot be deleted")
    if actor.role != "admin":
        raise PermissionError("Admin privileges required")
    deps = await TeamRepository.dependency_counts(team_id)
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


async def list_team_assignable_users_use_case(
    team_id: str,
    *,
    actor: CurrentUser,
    q: Optional[str],
    limit: int,
    offset: int,
) -> TeamAssignableUserListResponse:
    await _ensure_team_manager(team_id, actor)
    rows = await UserRepository.list_users(
        q=q,
        role=None,
        status="active",
        limit=limit,
        offset=offset,
    )
    total = await UserRepository.count_users(q=q, role=None, status="active")
    return TeamAssignableUserListResponse(
        items=[_team_member_user(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


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


async def list_team_models_use_case(
    team_id: str, *, actor: CurrentUser
) -> TeamModelAllowlistResponse:
    await _ensure_workspace_team_for_allowlist(team_id, actor)
    rows = await TeamAllowlistRepository.list_team_models(team_id)
    return _team_model_allowlist_response(team_id, rows)


async def replace_team_models_use_case(
    team_id: str,
    request: TeamModelAllowlistUpdateRequest,
    *,
    actor: CurrentUser,
) -> TeamModelAllowlistResponse:
    await _ensure_workspace_team_for_admin_allowlist(team_id, actor)
    for model_id in request.model_ids:
        if not await Model.get(model_id):
            raise NotFoundError("Model not found")

    rows = await TeamAllowlistRepository.replace_team_models(
        team_id,
        request.model_ids,
        actor.id,
    )
    await TeamRepository.clear_invalid_model_defaults(team_id, request.model_ids)
    await AuditLogRepository.create(
        action="team.models_updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata={"model_ids": request.model_ids},
    )
    return _team_model_allowlist_response(team_id, rows)


async def list_team_model_defaults_use_case(
    team_id: str, *, actor: CurrentUser
) -> TeamModelDefaultsResponse:
    team = await _ensure_workspace_team_for_allowlist(team_id, actor)
    return _team_model_defaults_response(team_id, team)


async def update_team_model_defaults_use_case(
    team_id: str,
    request: TeamModelDefaultsUpdateRequest,
    *,
    actor: CurrentUser,
) -> TeamModelDefaultsResponse:
    await _ensure_workspace_team_for_allowlist(team_id, actor)
    allowed_models = _allowed_team_models(
        await TeamAllowlistRepository.list_team_models(team_id)
    )
    updates = _validate_team_model_defaults(request, allowed_models)
    row = await TeamRepository.update_model_defaults(team_id, updates)
    await AuditLogRepository.create(
        action="team.model_defaults_updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata=updates,
    )
    return _team_model_defaults_response(team_id, row)


async def list_team_transformations_use_case(
    team_id: str, *, actor: CurrentUser
) -> TeamTransformationAllowlistResponse:
    await _ensure_workspace_team_for_allowlist(team_id, actor)
    rows = await TeamAllowlistRepository.list_team_transformations(team_id)
    return _team_transformation_allowlist_response(team_id, rows)


async def replace_team_transformations_use_case(
    team_id: str,
    request: TeamTransformationAllowlistUpdateRequest,
    *,
    actor: CurrentUser,
) -> TeamTransformationAllowlistResponse:
    await _ensure_workspace_team_for_admin_allowlist(team_id, actor)
    for transformation_id in request.transformation_ids:
        if not await Transformation.get(transformation_id):
            raise NotFoundError("Transformation not found")

    rows = await TeamAllowlistRepository.replace_team_transformations(
        team_id,
        request.transformation_ids,
        actor.id,
    )
    await AuditLogRepository.create(
        action="team.transformations_updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="team",
        target_id=team_id,
        metadata={"transformation_ids": request.transformation_ids},
    )
    return _team_transformation_allowlist_response(team_id, rows)
