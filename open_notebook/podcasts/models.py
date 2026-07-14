from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

from loguru import logger
from pydantic import ConfigDict, Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel


async def _resolve_model_config(
    model_id: str, max_tokens: Optional[int] = None
) -> Tuple[str, str, dict]:
    """Load Model record, resolve credential -> (provider, model_name, config_dict).

    Used by resolve_outline_config, resolve_transcript_config, resolve_tts_config,
    and per-speaker TTS overrides. Optionally passes through a max_tokens override.
    """
    from open_notebook.ai.models import Model

    model = await Model.get(model_id)
    config: dict = {}
    if model.credential:
        credential = await model.get_credential_obj()
        if credential:
            config = credential.to_esperanto_config()
    if not config:
        from open_notebook.ai.key_provider import provision_provider_keys

        await provision_provider_keys(model.provider)
    if max_tokens is not None:
        config = {**config, "max_tokens": max_tokens}
    return (model.provider, model.name, config)


class EpisodeProfile(ObjectModel):
    """
    Episode Profile - Simplified podcast configuration.
    Replaces complex 15+ field configuration with user-friendly profiles.
    """

    table_name: ClassVar[str] = "episode_profile"
    nullable_fields: ClassVar[set[str]] = {
        "description",
        "speaker_config",
        "outline_llm",
        "transcript_llm",
        "language",
        "max_tokens",
    }

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    speaker_config: Optional[str] = Field(
        None,
        description=(
            "speaker_profile record ID this profile uses. None when the "
            "referenced speaker profile no longer exists (orphaned by "
            "migration 20 or a later deletion)."
        ),
    )

    # Model registry references
    outline_llm: Optional[str] = Field(
        None, description="Model record ID for outline generation"
    )
    transcript_llm: Optional[str] = Field(
        None, description="Model record ID for transcript generation"
    )
    language: Optional[str] = Field(
        None, description="Podcast language (BCP 47 locale code, e.g. pt-BR, en-US)"
    )

    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")
    max_tokens: Optional[int] = Field(
        None,
        description="Max output tokens for outline/transcript generation (passed through to podcast_creator)",
    )

    @field_validator("num_segments")
    @classmethod
    def validate_segments(cls, v):
        if not 3 <= v <= 20:
            raise ValueError("Number of segments must be between 3 and 20")
        return v

    def _prepare_save_data(self) -> dict:
        data = super()._prepare_save_data()
        if data.get("speaker_config"):
            data["speaker_config"] = ensure_record_id(data["speaker_config"])
        if data.get("outline_llm"):
            data["outline_llm"] = ensure_record_id(data["outline_llm"])
        if data.get("transcript_llm"):
            data["transcript_llm"] = ensure_record_id(data["transcript_llm"])
        return data

    async def resolve_outline_config(self) -> Tuple[str, str, dict]:
        """Resolve outline model -> (provider, model_name, config_dict)"""
        if not self.outline_llm:
            raise ValueError(
                f"Episode profile '{self.name}' has no outline model configured. "
                "Please update the profile to select an outline model."
            )
        return await _resolve_model_config(self.outline_llm, max_tokens=self.max_tokens)

    async def resolve_transcript_config(self) -> Tuple[str, str, dict]:
        """Resolve transcript model -> (provider, model_name, config_dict)"""
        if not self.transcript_llm:
            raise ValueError(
                f"Episode profile '{self.name}' has no transcript model configured. "
                "Please update the profile to select a transcript model."
            )
        return await _resolve_model_config(
            self.transcript_llm, max_tokens=self.max_tokens
        )

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["EpisodeProfile"]:
        """Get episode profile by name"""
        result = await repo_query(
            "SELECT * FROM episode_profile WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None


class SpeakerProfile(ObjectModel):
    """
    Speaker Profile - Voice and personality configuration.
    Supports 1-4 speakers for flexible podcast formats.
    """

    table_name: ClassVar[str] = "speaker_profile"
    nullable_fields: ClassVar[set[str]] = {
        "description",
        "voice_model",
    }

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")

    # Model registry reference
    voice_model: Optional[str] = Field(
        None, description="Model record ID for TTS"
    )

    speakers: List[Dict[str, Any]] = Field(
        ..., description="Array of speaker configurations"
    )

    @field_validator("speakers")
    @classmethod
    def validate_speakers(cls, v):
        if not 1 <= len(v) <= 4:
            raise ValueError("Must have between 1 and 4 speakers")

        required_fields = ["name", "voice_id", "backstory", "personality"]
        for speaker in v:
            for field in required_fields:
                if field not in speaker:
                    raise ValueError(f"Speaker missing required field: {field}")
        return v

    def _prepare_save_data(self) -> dict:
        data = super()._prepare_save_data()
        if data.get("voice_model"):
            data["voice_model"] = ensure_record_id(data["voice_model"])
        # Handle per-speaker voice_model overrides
        if data.get("speakers"):
            for speaker in data["speakers"]:
                if speaker.get("voice_model"):
                    speaker["voice_model"] = ensure_record_id(speaker["voice_model"])
        return data

    async def resolve_tts_config(self) -> Tuple[str, str, dict]:
        """Resolve TTS model -> (provider, model_name, config_dict)"""
        if not self.voice_model:
            raise ValueError(
                f"Speaker profile '{self.name}' has no voice model configured. "
                "Please update the profile to select a voice model."
            )
        return await _resolve_model_config(self.voice_model)

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["SpeakerProfile"]:
        """Get speaker profile by name"""
        result = await repo_query(
            "SELECT * FROM speaker_profile WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

    @classmethod
    async def resolve(
        cls, ref: Union[str, RecordID]
    ) -> Optional["SpeakerProfile"]:
        """Resolve a speaker profile by record ID or by unique name.

        The API contract accepts speaker profiles by NAME (see
        POST /api/podcasts/generate), while episode_profile.speaker_config
        stores a record ID (migration 20). This resolves either form and
        returns None when the reference doesn't match anything.
        """
        ref_str = str(ref)
        if ref_str.startswith(f"{cls.table_name}:"):
            result = await repo_query(
                "SELECT * FROM $id", {"id": ensure_record_id(ref_str)}
            )
            if result:
                return cls(**result[0])
            return None
        return await cls.get_by_name(ref_str)


class PodcastEpisode(ObjectModel):
    """Enhanced PodcastEpisode with job tracking and metadata"""

    table_name: ClassVar[str] = "episode"

    name: str = Field(..., description="Episode name")
    episode_profile: Dict[str, Any] = Field(
        ..., description="Episode profile used (stored as object)"
    )
    speaker_profile: Dict[str, Any] = Field(
        ..., description="Speaker profile used (stored as object)"
    )
    briefing: str = Field(..., description="Full briefing used for generation")
    content: str = Field(..., description="Source content")
    audio_file: Optional[str] = Field(
        default=None,
        description=(
            "Path to the generated audio file, relative to PODCASTS_FOLDER "
            "(see open_notebook/podcasts/audio_paths.py). Absolute values "
            "are legacy rows migration 21 could not convert and are treated "
            "as invalid by the API."
        ),
    )
    transcript: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Generated transcript"
    )
    outline: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Generated outline"
    )
    command: Optional[Union[str, RecordID]] = Field(
        default=None, description="Link to surreal-commands job"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def get_job_status(self) -> Optional[str]:
        """Get the status of the associated command"""
        if not self.command:
            return None

        try:
            from surreal_commands import get_command_status

            status = await get_command_status(str(self.command))
            return status.status if status else "unknown"
        except Exception:
            return "unknown"

    async def get_job_detail(self) -> dict:
        """Get status and error_message of the associated command"""
        if not self.command:
            return {"status": None, "error_message": None}

        try:
            from surreal_commands import get_command_status

            status = await get_command_status(str(self.command))
            if not status:
                return {"status": "unknown", "error_message": None}
            return {
                "status": status.status,
                "error_message": getattr(status, "error_message", None),
            }
        except Exception:
            return {"status": "unknown", "error_message": None}

    @classmethod
    async def get_job_details_for_commands(
        cls, command_ids: List[Union[str, RecordID]]
    ) -> Dict[str, dict]:
        """
        Batch-fetch {status, error_message} for many commands in one query.

        Listing episodes otherwise calls get_job_detail() -> surreal_commands
        .get_command_status() once per episode, each its own round trip
        against the `command` table (no connection pooling in the repository
        layer, see docs/7-DEVELOPMENT/architecture.md) - O(n) queries for n
        episodes. surreal_commands has no batch lookup, but its command table
        lives in the same database (same SURREAL_* env vars), so this queries
        it directly in one shot instead of looping through the library's
        per-command helper.

        CommandStatus is a `str` subclass (`class CommandStatus(str, Enum)`),
        so returning the raw DB string here is interchangeable with the
        enum-wrapped value get_job_detail() returns for every comparison
        this codebase does against it.
        """
        ids = [cid for cid in command_ids if cid]
        grouped: Dict[str, dict] = {}
        if not ids:
            return grouped
        try:
            result = await repo_query(
                "SELECT * FROM command WHERE id IN $command_ids",
                {"command_ids": [ensure_record_id(cid) for cid in ids]},
            )
        except Exception as e:
            logger.error(f"Error batch-fetching command status: {e}")
            return grouped
        for row in result:
            grouped[str(row.get("id"))] = {
                "status": row.get("status", "unknown"),
                "error_message": row.get("error_message"),
            }
        return grouped

    @field_validator("command", mode="before")
    @classmethod
    def parse_command(cls, value):
        if isinstance(value, str):
            return ensure_record_id(value)
        return value

    def _prepare_save_data(self) -> dict:
        """Override to ensure command field is always RecordID format for database"""
        data = super()._prepare_save_data()

        # Ensure command field is RecordID format if not None
        if data.get("command") is not None:
            data["command"] = ensure_record_id(data["command"])

        return data
