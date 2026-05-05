from __future__ import annotations

from typing import Optional

from api.auth import CurrentUser
from open_notebook.database.repositories.share_repository import (
    PUBLIC_TEAM_ID,
    ShareRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.exceptions import InvalidInputError


READ_PERMISSIONS = {"read", "write", "owner"}


async def resolve_resource_team_context(
    *,
    resource_type: str,
    resource_id: str,
) -> Optional[str]:
    """Infer a team context from a resource with exactly one non-public team grant."""
    grants = await ShareRepository.list_resource_grants(
        resource_type=resource_type,
        resource_id=resource_id,
    )
    team_ids = {
        str(grant.get("target_id"))
        for grant in grants
        if grant.get("target_type") == "team"
        and grant.get("target_id")
        and str(grant.get("target_id")) != PUBLIC_TEAM_ID
        and grant.get("permission") in READ_PERMISSIONS
    }
    if len(team_ids) == 1:
        return next(iter(team_ids))
    return None


async def resolve_explicit_team_context(
    *,
    actor: Optional[CurrentUser],
    team_id: Optional[str],
) -> Optional[str]:
    if not team_id:
        return None
    if actor is None or actor.role == "admin":
        return team_id

    member = await TeamRepository.get_member(team_id, actor.id)
    if not member or member.get("status") != "active":
        raise InvalidInputError("Team access required")
    return team_id


async def resolve_team_context(
    *,
    actor: Optional[CurrentUser],
    explicit_team_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> Optional[str]:
    if explicit_team_id:
        return await resolve_explicit_team_context(
            actor=actor,
            team_id=explicit_team_id,
        )
    if resource_type and resource_id:
        team_id = await resolve_resource_team_context(
            resource_type=resource_type,
            resource_id=resource_id,
        )
        if team_id:
            return await resolve_explicit_team_context(actor=actor, team_id=team_id)
    return None
