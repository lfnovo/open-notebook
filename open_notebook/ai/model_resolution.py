from __future__ import annotations

from typing import Optional

from loguru import logger

from open_notebook.ai.models import DefaultModels
from open_notebook.database.repositories.team_allowlist_repository import (
    TeamAllowlistRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository


MODEL_SLOT_FIELDS = {
    "chat": "default_chat_model",
    "embedding": "default_embedding_model",
    "transformation": "default_transformation_model",
    "tools": "default_tools_model",
    "large_context": "large_context_model",
    "text_to_speech": "default_text_to_speech_model",
    "speech_to_text": "default_speech_to_text_model",
}

TEAM_MODEL_SLOT_TYPES = {
    "chat": "language",
    "embedding": "embedding",
    "transformation": "language",
    "tools": "language",
    "large_context": "language",
}


def _string_value(value: object) -> Optional[str]:
    return str(value) if value else None


def _system_default_id(defaults: DefaultModels, default_type: str) -> Optional[str]:
    if default_type == "transformation":
        return _string_value(
            defaults.default_transformation_model or defaults.default_chat_model
        )
    if default_type == "tools":
        return _string_value(defaults.default_tools_model or defaults.default_chat_model)

    field = MODEL_SLOT_FIELDS.get(default_type)
    if not field:
        return None
    return _string_value(getattr(defaults, field, None))


def _allowed_team_models(rows: list[dict]) -> dict[str, dict]:
    return {
        str(row["model"]["id"]): row["model"]
        for row in rows
        if isinstance(row.get("model"), dict) and row["model"].get("id")
    }


async def resolve_default_model_id(
    default_type: str,
    *,
    team_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve the effective default model id for a system or team context."""
    defaults = await DefaultModels.get_instance()
    system_model_id = _system_default_id(defaults, default_type)

    if not team_id or default_type not in TEAM_MODEL_SLOT_TYPES:
        return system_model_id

    team = await TeamRepository.get_team(team_id)
    if not team or team.get("type") == "system":
        return system_model_id

    field = MODEL_SLOT_FIELDS[default_type]
    team_model_id = _string_value(team.get(field))
    if not team_model_id:
        return system_model_id

    allowed_models = _allowed_team_models(
        await TeamAllowlistRepository.list_team_models(team_id)
    )
    model = allowed_models.get(team_model_id)
    if not model:
        logger.warning(
            f"Team default model {team_model_id} for {default_type} is not in "
            f"{team_id}'s allowlist; falling back to system default"
        )
        return system_model_id

    expected_type = TEAM_MODEL_SLOT_TYPES[default_type]
    if model.get("type") != expected_type:
        logger.warning(
            f"Team default model {team_model_id} for {default_type} has type "
            f"{model.get('type')}; expected {expected_type}. Falling back to "
            "system default"
        )
        return system_model_id

    return team_model_id
