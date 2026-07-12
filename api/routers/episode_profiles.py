from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.exceptions import InvalidInputError, OpenNotebookError
from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile

router = APIRouter()


class EpisodeProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    speaker_config: Optional[str] = Field(
        None, description="speaker_profile record ID (null when orphaned)"
    )
    speaker_config_name: Optional[str] = Field(
        None, description="Resolved speaker profile name (for display)"
    )
    outline_llm: Optional[str] = None
    transcript_llm: Optional[str] = None
    language: Optional[str] = None
    default_briefing: str
    num_segments: int
    max_tokens: Optional[int] = None
    # Legacy fields (for display/migration awareness)
    outline_provider: Optional[str] = None
    outline_model: Optional[str] = None
    transcript_provider: Optional[str] = None
    transcript_model: Optional[str] = None


async def _speaker_names_by_id() -> Dict[str, str]:
    """Map speaker_profile record ID -> name for list serialization."""
    speakers = await SpeakerProfile.get_all()
    return {str(speaker.id): speaker.name for speaker in speakers}


async def _speaker_name_for(speaker_config: Optional[str]) -> Optional[str]:
    """Resolve one profile's speaker_config record ID to the speaker name.

    Returns None for a missing or dangling reference - the frontend renders
    that as "needs setup"."""
    if not speaker_config:
        return None
    speaker = await SpeakerProfile.resolve(speaker_config)
    return speaker.name if speaker else None


def _profile_to_response(
    profile: EpisodeProfile, speaker_name: Optional[str]
) -> EpisodeProfileResponse:
    return EpisodeProfileResponse(
        id=str(profile.id),
        name=profile.name,
        description=profile.description or "",
        speaker_config=profile.speaker_config,
        speaker_config_name=speaker_name,
        outline_llm=profile.outline_llm,
        transcript_llm=profile.transcript_llm,
        language=profile.language,
        default_briefing=profile.default_briefing,
        num_segments=profile.num_segments,
        max_tokens=profile.max_tokens,
        outline_provider=profile.outline_provider,
        outline_model=profile.outline_model,
        transcript_provider=profile.transcript_provider,
        transcript_model=profile.transcript_model,
    )


async def _resolve_speaker_config(value: str) -> SpeakerProfile:
    """Resolve an incoming speaker_config (record ID, or name for backward
    compatibility) to the referenced SpeakerProfile."""
    speaker = await SpeakerProfile.resolve(value)
    if not speaker:
        raise InvalidInputError(f"Speaker profile '{value}' not found")
    return speaker


@router.get("/episode-profiles", response_model=List[EpisodeProfileResponse])
async def list_episode_profiles():
    """List all available episode profiles"""
    try:
        profiles = await EpisodeProfile.get_all(order_by="name asc")
        speaker_names = await _speaker_names_by_id()
        return [
            _profile_to_response(
                p, speaker_names.get(p.speaker_config) if p.speaker_config else None
            )
            for p in profiles
        ]
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch episode profiles: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch episode profiles"
        )


@router.get("/episode-profiles/{profile_name}", response_model=EpisodeProfileResponse)
async def get_episode_profile(profile_name: str):
    """Get a specific episode profile by name"""
    try:
        profile = await EpisodeProfile.get_by_name(profile_name)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Episode profile '{profile_name}' not found"
            )

        return _profile_to_response(
            profile, await _speaker_name_for(profile.speaker_config)
        )

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch episode profile '{profile_name}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch episode profile"
        )


class EpisodeProfileCreate(BaseModel):
    name: str = Field(..., description="Unique profile name")
    description: str = Field("", description="Profile description")
    speaker_config: str = Field(
        ...,
        description=(
            "speaker_profile record ID (a profile name is also accepted "
            "for backward compatibility)"
        ),
    )
    outline_llm: Optional[str] = Field(None, description="Model record ID for outline")
    transcript_llm: Optional[str] = Field(
        None, description="Model record ID for transcript"
    )
    language: Optional[str] = Field(None, description="Podcast language code")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")
    max_tokens: Optional[int] = Field(
        None,
        description="Max output tokens for outline/transcript generation",
    )
    # Legacy fields (accepted but not required)
    outline_provider: Optional[str] = None
    outline_model: Optional[str] = None
    transcript_provider: Optional[str] = None
    transcript_model: Optional[str] = None


@router.post("/episode-profiles", response_model=EpisodeProfileResponse)
async def create_episode_profile(profile_data: EpisodeProfileCreate):
    """Create a new episode profile"""
    try:
        speaker = await _resolve_speaker_config(profile_data.speaker_config)
        profile = EpisodeProfile(
            name=profile_data.name,
            description=profile_data.description,
            speaker_config=str(speaker.id),
            outline_llm=profile_data.outline_llm,
            transcript_llm=profile_data.transcript_llm,
            language=profile_data.language,
            default_briefing=profile_data.default_briefing,
            num_segments=profile_data.num_segments,
            max_tokens=profile_data.max_tokens,
            outline_provider=profile_data.outline_provider,
            outline_model=profile_data.outline_model,
            transcript_provider=profile_data.transcript_provider,
            transcript_model=profile_data.transcript_model,
        )

        await profile.save()
        return _profile_to_response(profile, speaker.name)

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to create episode profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create episode profile"
        )


@router.put("/episode-profiles/{profile_id}", response_model=EpisodeProfileResponse)
async def update_episode_profile(profile_id: str, profile_data: EpisodeProfileCreate):
    """Update an existing episode profile"""
    try:
        profile = await EpisodeProfile.get(profile_id)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Episode profile '{profile_id}' not found"
            )

        update_data = profile_data.model_dump(exclude_unset=True)
        speaker_name: Optional[str] = None
        if "speaker_config" in update_data:
            speaker = await _resolve_speaker_config(update_data["speaker_config"])
            update_data["speaker_config"] = str(speaker.id)
            speaker_name = speaker.name
        for field, value in update_data.items():
            setattr(profile, field, value)

        await profile.save()
        if speaker_name is None:
            speaker_name = await _speaker_name_for(profile.speaker_config)
        return _profile_to_response(profile, speaker_name)

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to update episode profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update episode profile"
        )


@router.delete("/episode-profiles/{profile_id}")
async def delete_episode_profile(profile_id: str):
    """Delete an episode profile"""
    try:
        profile = await EpisodeProfile.get(profile_id)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Episode profile '{profile_id}' not found"
            )

        await profile.delete()

        return {"message": "Episode profile deleted successfully"}

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to delete episode profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete episode profile"
        )


@router.post(
    "/episode-profiles/{profile_id}/duplicate", response_model=EpisodeProfileResponse
)
async def duplicate_episode_profile(profile_id: str):
    """Duplicate an episode profile"""
    try:
        original = await EpisodeProfile.get(profile_id)

        if not original:
            raise HTTPException(
                status_code=404, detail=f"Episode profile '{profile_id}' not found"
            )

        duplicate = EpisodeProfile(
            name=f"{original.name} - Copy",
            description=original.description,
            speaker_config=original.speaker_config,
            outline_llm=original.outline_llm,
            transcript_llm=original.transcript_llm,
            language=original.language,
            default_briefing=original.default_briefing,
            num_segments=original.num_segments,
            max_tokens=original.max_tokens,
            outline_provider=original.outline_provider,
            outline_model=original.outline_model,
            transcript_provider=original.transcript_provider,
            transcript_model=original.transcript_model,
        )

        await duplicate.save()
        return _profile_to_response(
            duplicate, await _speaker_name_for(duplicate.speaker_config)
        )

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate episode profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to duplicate episode profile"
        )
