from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

from loguru import logger
from pydantic import ConfigDict, Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel


async def _resolve_model_config(model_id: str) -> Tuple[str, str, dict]:
    """Load Model record, resolve credential -> (provider, model_name, config_dict).

    Used by resolve_outline_config, resolve_transcript_config, resolve_tts_config,
    and per-speaker TTS overrides.
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
    return (model.provider, model.name, config)


class EpisodeProfile(ObjectModel):
    """
    Episode Profile - Simplified podcast configuration.
    Replaces complex 15+ field configuration with user-friendly profiles.
    """

    table_name: ClassVar[str] = "episode_profile"
    nullable_fields: ClassVar[set[str]] = {
        "description",
        "outline_provider",
        "outline_model",
        "transcript_provider",
        "transcript_model",
        "outline_llm",
        "transcript_llm",
        "language",
    }

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")

    # Legacy fields (kept for migration, app ignores)
    outline_provider: Optional[str] = Field(
        None, description="[Legacy] AI provider for outline generation"
    )
    outline_model: Optional[str] = Field(
        None, description="[Legacy] AI model for outline generation"
    )
    transcript_provider: Optional[str] = Field(
        None, description="[Legacy] AI provider for transcript generation"
    )
    transcript_model: Optional[str] = Field(
        None, description="[Legacy] AI model for transcript generation"
    )

    # New fields: Model registry references
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

    @field_validator("num_segments")
    @classmethod
    def validate_segments(cls, v):
        if not 3 <= v <= 20:
            raise ValueError("Number of segments must be between 3 and 20")
        return v

    def _prepare_save_data(self) -> dict:
        data = super()._prepare_save_data()
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
        return await _resolve_model_config(self.outline_llm)

    async def resolve_transcript_config(self) -> Tuple[str, str, dict]:
        """Resolve transcript model -> (provider, model_name, config_dict)"""
        if not self.transcript_llm:
            raise ValueError(
                f"Episode profile '{self.name}' has no transcript model configured. "
                "Please update the profile to select a transcript model."
            )
        return await _resolve_model_config(self.transcript_llm)

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
        "tts_provider",
        "tts_model",
        "voice_model",
    }

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")

    # Legacy fields (kept for migration, app ignores)
    tts_provider: Optional[str] = Field(
        None, description="[Legacy] TTS provider (openai, elevenlabs, etc.)"
    )
    tts_model: Optional[str] = Field(None, description="[Legacy] TTS model name")

    # New field: Model registry reference
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
        default=None, description="Path to generated audio file"
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
