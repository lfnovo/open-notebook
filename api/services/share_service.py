from __future__ import annotations

import os

from api.auth import CurrentUser
from api.models import DeleteResponse, ShareGrantCreateRequest, ShareGrantResponse
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.share_repository import (
    PUBLIC_TEAM_ID,
    ShareRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.user_repository import UserRepository
from open_notebook.database.repository import repo_update
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError, NotFoundError


def _grant_response(row: dict) -> ShareGrantResponse:
    return ShareGrantResponse(
        id=str(row.get("id", "")),
        resource_type=row.get("resource_type", "source"),
        resource_id=row.get("resource_id", ""),
        target_type=row.get("target_type", "team"),
        target_id=row.get("target_id", ""),
        permission=row.get("permission", "read"),
        created_by=str(row.get("created_by", "")) if row.get("created_by") else None,
        created=str(row.get("created", "")),
    )


async def _resource_owner(resource_type: str, resource_id: str) -> str | None:
    if resource_type == "source":
        source = await Source.get(resource_id)
        if not source:
            raise NotFoundError("Source not found")
        return str(source.owner_id) if source.owner_id else None
    if resource_type == "notebook":
        notebook = await Notebook.get(resource_id)
        if not notebook:
            raise NotFoundError("Notebook not found")
        return str(notebook.owner_id) if notebook.owner_id else None
    raise InvalidInputError("Invalid resource type")


async def can_read_resource(
    *,
    resource_type: str,
    resource_id: str,
    user_id: str | None,
    owner_id: str | None,
    visibility: str,
) -> bool:
    if visibility == "public":
        return True
    if user_id and owner_id and str(owner_id) == str(user_id):
        return True
    team_ids = await TeamRepository.user_team_ids(user_id) if user_id else []
    return await ShareRepository.has_read_grant(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        team_ids=team_ids,
    )


async def _ensure_share_manager(
    resource_type: str, resource_id: str, actor: CurrentUser
) -> None:
    owner_id = await _resource_owner(resource_type, resource_id)
    if actor.role == "admin":
        return
    if owner_id and owner_id == actor.id:
        return
    raise PermissionError("Only the resource owner or an admin can manage sharing")


async def list_resource_grants_use_case(
    *,
    resource_type: str,
    resource_id: str,
    actor: CurrentUser,
) -> list[ShareGrantResponse]:
    await _ensure_share_manager(resource_type, resource_id, actor)
    rows = await ShareRepository.list_resource_grants(
        resource_type=resource_type, resource_id=resource_id
    )
    return [_grant_response(row) for row in rows]


async def create_share_grant_use_case(
    request: ShareGrantCreateRequest,
    *,
    actor: CurrentUser,
) -> ShareGrantResponse:
    await _ensure_share_manager(request.resource_type, request.resource_id, actor)
    if request.permission != "read":
        raise InvalidInputError("Only read sharing is supported in this phase")

    if request.target_type == "team":
        team = await TeamRepository.get_team(request.target_id)
        if not team:
            raise NotFoundError("Team not found")
    elif request.target_type == "user":
        user = await UserRepository.get_user(request.target_id)
        if not user:
            raise NotFoundError("User not found")
        if user.get("status", "active") != "active":
            raise InvalidInputError("Only active users can receive share grants")

    row = await ShareRepository.create_grant(
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        target_type=request.target_type,
        target_id=request.target_id,
        permission=request.permission,
        created_by=actor.id,
    )

    if request.target_type == "team" and request.target_id == PUBLIC_TEAM_ID:
        table = "source" if request.resource_type == "source" else "notebook"
        await repo_update(table, request.resource_id, {"visibility": "public"})
        action = "share.public_enabled"
    else:
        action = "share.created"

    await AuditLogRepository.create(
        action=action,
        actor_id=actor.id,
        actor_username=actor.username,
        target_type=request.resource_type,
        target_id=request.resource_id,
        metadata={
            "target_type": request.target_type,
            "target_id": request.target_id,
            "permission": request.permission,
        },
    )
    return _grant_response(row or {})


def _public_revocation_mode() -> str:
    mode = os.getenv("PUBLIC_SHARE_REVOCATION_MODE", "preserve_references")
    if mode not in {"preserve_references", "block_if_referenced", "revoke_all"}:
        return "preserve_references"
    return mode


async def delete_share_grant_use_case(
    grant_id: str,
    *,
    actor: CurrentUser,
) -> DeleteResponse:
    grant = await ShareRepository.get_grant(grant_id)
    if not grant:
        raise NotFoundError("Share grant not found")
    await _ensure_share_manager(grant["resource_type"], grant["resource_id"], actor)

    is_public = grant.get("target_type") == "team" and grant.get("target_id") == PUBLIC_TEAM_ID
    preserved_count = 0
    affected_reference_count = 0
    if is_public:
        mode = _public_revocation_mode()
        referencing_owners = await ShareRepository.referencing_notebook_owner_ids(
            grant["resource_type"], grant["resource_id"]
        )
        affected_reference_count = len(referencing_owners)
        if mode == "block_if_referenced" and referencing_owners:
            raise InvalidInputError(
                "Cannot revoke public access while the resource has active references"
            )
        if mode == "preserve_references":
            for owner_id in referencing_owners:
                if owner_id != actor.id:
                    preserved = await ShareRepository.create_grant(
                        resource_type=grant["resource_type"],
                        resource_id=grant["resource_id"],
                        target_type="user",
                        target_id=owner_id,
                        permission="read",
                        created_by=actor.id,
                    )
                    if preserved:
                        preserved_count += 1
            if grant["resource_type"] == "notebook":
                existing_notebook_grants = await ShareRepository.list_resource_grants(
                    resource_type="notebook", resource_id=grant["resource_id"]
                )
                source_ids = await ShareRepository.notebook_source_ids(grant["resource_id"])
                for notebook_grant in existing_notebook_grants:
                    target_type = notebook_grant.get("target_type")
                    target_id = notebook_grant.get("target_id")
                    if target_type == "team" and target_id == PUBLIC_TEAM_ID:
                        continue
                    if target_type not in {"user", "team"} or not target_id:
                        continue
                    for source_id in source_ids:
                        preserved = await ShareRepository.create_grant(
                            resource_type="source",
                            resource_id=source_id,
                            target_type=target_type,
                            target_id=target_id,
                            permission="read",
                            created_by=actor.id,
                        )
                        if preserved:
                            preserved_count += 1

    await ShareRepository.delete_grant(grant_id)

    if is_public:
        table = "source" if grant["resource_type"] == "source" else "notebook"
        await repo_update(table, grant["resource_id"], {"visibility": "private"})
        action = "share.public_revoked"
    else:
        action = "share.revoked"

    await AuditLogRepository.create(
        action=action,
        actor_id=actor.id,
        actor_username=actor.username,
        target_type=grant["resource_type"],
        target_id=grant["resource_id"],
        metadata={
            "grant_id": grant_id,
            "preserved_grants_count": preserved_count,
            "affected_reference_count": affected_reference_count,
        },
    )
    return DeleteResponse(success=True, message="Share grant deleted")
