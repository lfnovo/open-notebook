from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from open_notebook.domain.podcast import EpisodeProfile


router = APIRouter()


class EpisodeProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    speaker_config: str
    outline_provider: str
    outline_model: str
    transcript_provider: str
    transcript_model: str
    default_briefing: str
    num_segments: int


@router.get("/episode-profiles", response_model=List[EpisodeProfileResponse])
async def list_episode_profiles():
    """List all available episode profiles"""
    try:
        profiles = await EpisodeProfile.get_all(order_by="name asc")
        
        return [
            EpisodeProfileResponse(
                id=str(profile.id),
                name=profile.name,
                description=profile.description or "",
                speaker_config=profile.speaker_config,
                outline_provider=profile.outline_provider,
                outline_model=profile.outline_model,
                transcript_provider=profile.transcript_provider,
                transcript_model=profile.transcript_model,
                default_briefing=profile.default_briefing,
                num_segments=profile.num_segments
            )
            for profile in profiles
        ]
        
    except Exception as e:
        logger.error(f"Failed to fetch episode profiles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch episode profiles: {str(e)}"
        )


@router.get("/episode-profiles/{profile_name}", response_model=EpisodeProfileResponse)
async def get_episode_profile(profile_name: str):
    """Get a specific episode profile by name"""
    try:
        profile = await EpisodeProfile.get_by_name(profile_name)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Episode profile '{profile_name}' not found"
            )
        
        return EpisodeProfileResponse(
            id=str(profile.id),
            name=profile.name,
            description=profile.description or "",
            speaker_config=profile.speaker_config,
            outline_provider=profile.outline_provider,
            outline_model=profile.outline_model,
            transcript_provider=profile.transcript_provider,
            transcript_model=profile.transcript_model,
            default_briefing=profile.default_briefing,
            num_segments=profile.num_segments
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch episode profile '{profile_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch episode profile: {str(e)}"
        )