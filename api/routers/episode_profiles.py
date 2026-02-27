from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.podcasts.models import EpisodeProfile

router = APIRouter()


class EpisodeProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    speaker_config: str
    outline_llm: Optional[str] = None
    transcript_llm: Optional[str] = None
    language: Optional[str] = None
    default_briefing: str
    num_segments: int
    # Legacy fields (for display/migration awareness)
    outline_provider: Optional[str] = None
    outline_model: Optional[str] = None
    transcript_provider: Optional[str] = None
    transcript_model: Optional[str] = None


def _profile_to_response(profile: EpisodeProfile) -> EpisodeProfileResponse:
    return EpisodeProfileResponse(
        id=str(profile.id),
        name=profile.name,
        description=profile.description or "",
        speaker_config=profile.speaker_config,
        outline_llm=profile.outline_llm,
        transcript_llm=profile.transcript_llm,
        language=profile.language,
        default_briefing=profile.default_briefing,
        num_segments=profile.num_segments,
        outline_provider=profile.outline_provider,
        outline_model=profile.outline_model,
        transcript_provider=profile.transcript_provider,
        transcript_model=profile.transcript_model,
    )


@router.get("/episode-profiles", response_model=List[EpisodeProfileResponse])
async def list_episode_profiles():
    """List all available episode profiles"""
    try:
        profiles = await EpisodeProfile.get_all(order_by="name asc")
        return [_profile_to_response(p) for p in profiles]
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

        return _profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch episode profile '{profile_name}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch episode profile"
        )


class EpisodeProfileCreate(BaseModel):
    name: str = Field(..., description="Unique profile name")
    description: str = Field("", description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")
    outline_llm: Optional[str] = Field(None, description="Model record ID for outline")
    transcript_llm: Optional[str] = Field(
        None, description="Model record ID for transcript"
    )
    language: Optional[str] = Field(None, description="Podcast language code")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")
    # Legacy fields (accepted but not required)
    outline_provider: Optional[str] = None
    outline_model: Optional[str] = None
    transcript_provider: Optional[str] = None
    transcript_model: Optional[str] = None


@router.post("/episode-profiles", response_model=EpisodeProfileResponse)
async def create_episode_profile(profile_data: EpisodeProfileCreate):
    """Create a new episode profile"""
    try:
        profile = EpisodeProfile(
            name=profile_data.name,
            description=profile_data.description,
            speaker_config=profile_data.speaker_config,
            outline_llm=profile_data.outline_llm,
            transcript_llm=profile_data.transcript_llm,
            language=profile_data.language,
            default_briefing=profile_data.default_briefing,
            num_segments=profile_data.num_segments,
            outline_provider=profile_data.outline_provider,
            outline_model=profile_data.outline_model,
            transcript_provider=profile_data.transcript_provider,
            transcript_model=profile_data.transcript_model,
        )

        await profile.save()
        return _profile_to_response(profile)

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

        profile.name = profile_data.name
        profile.description = profile_data.description
        profile.speaker_config = profile_data.speaker_config
        profile.outline_llm = profile_data.outline_llm
        profile.transcript_llm = profile_data.transcript_llm
        profile.language = profile_data.language
        profile.default_briefing = profile_data.default_briefing
        profile.num_segments = profile_data.num_segments
        profile.outline_provider = profile_data.outline_provider
        profile.outline_model = profile_data.outline_model
        profile.transcript_provider = profile_data.transcript_provider
        profile.transcript_model = profile_data.transcript_model

        await profile.save()
        return _profile_to_response(profile)

    except HTTPException:
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
            outline_provider=original.outline_provider,
            outline_model=original.outline_model,
            transcript_provider=original.transcript_provider,
            transcript_model=original.transcript_model,
        )

        await duplicate.save()
        return _profile_to_response(duplicate)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate episode profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to duplicate episode profile"
        )
