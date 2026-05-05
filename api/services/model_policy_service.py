from __future__ import annotations

from typing import Optional

from api.auth import CurrentUser
from open_notebook.ai.model_resolution import resolve_default_model_id
from open_notebook.exceptions import InvalidInputError


async def ensure_model_selection_allowed(
    *,
    actor: Optional[CurrentUser],
    model_id: Optional[str],
    default_type: str,
    team_id: Optional[str] = None,
) -> None:
    """Allow explicit model ids only when they match policy for the actor."""
    if not model_id:
        return
    if actor is None or actor.role == "admin":
        return

    effective_default = await resolve_default_model_id(
        default_type,
        team_id=team_id,
    )
    if model_id != effective_default:
        raise InvalidInputError(
            "Model selection is managed by the system or team administrator"
        )


async def ensure_model_selections_allowed(
    *,
    actor: Optional[CurrentUser],
    model_ids: list[Optional[str]],
    default_type: str,
    team_id: Optional[str] = None,
) -> None:
    for model_id in model_ids:
        await ensure_model_selection_allowed(
            actor=actor,
            model_id=model_id,
            default_type=default_type,
            team_id=team_id,
        )
