from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel


class EpisodeProfile(ObjectModel):
    """
    Episode Profile - Simplified podcast configuration.
    Replaces complex 15+ field configuration with user-friendly profiles.
    """

    table_name: ClassVar[str] = "episode_profile"

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")
    outline_provider: str = Field(..., description="AI provider for outline generation")
    outline_model: str = Field(..., description="AI model for outline generation")
    transcript_provider: str = Field(
        ..., description="AI provider for transcript generation"
    )
    transcript_model: str = Field(..., description="AI model for transcript generation")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")

    @field_validator("num_segments")
    @classmethod
    def validate_segments(cls, v):
        if not 3 <= v <= 20:
            raise ValueError("Number of segments must be between 3 and 20")
        return v

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

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    tts_provider: str = Field(
        ..., description="TTS provider (openai, elevenlabs, etc.)"
    )
    tts_model: str = Field(..., description="TTS model name")
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

    class Config:
        arbitrary_types_allowed = True

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
