from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

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


class EpisodeProfileCreate(BaseModel):
    name: str = Field(..., description="Unique profile name")
    description: str = Field("", description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")
    outline_provider: str = Field(..., description="AI provider for outline generation")
    outline_model: str = Field(..., description="AI model for outline generation")
    transcript_provider: str = Field(..., description="AI provider for transcript generation")
    transcript_model: str = Field(..., description="AI model for transcript generation")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")


@router.post("/episode-profiles", response_model=EpisodeProfileResponse)
async def create_episode_profile(profile_data: EpisodeProfileCreate):
    """Create a new episode profile"""
    try:
        profile = EpisodeProfile(
            name=profile_data.name,
            description=profile_data.description,
            speaker_config=profile_data.speaker_config,
            outline_provider=profile_data.outline_provider,
            outline_model=profile_data.outline_model,
            transcript_provider=profile_data.transcript_provider,
            transcript_model=profile_data.transcript_model,
            default_briefing=profile_data.default_briefing,
            num_segments=profile_data.num_segments
        )
        
        await profile.save()
        
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
        
    except Exception as e:
        logger.error(f"Failed to create episode profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create episode profile: {str(e)}"
        )


@router.put("/episode-profiles/{profile_id}", response_model=EpisodeProfileResponse)
async def update_episode_profile(profile_id: str, profile_data: EpisodeProfileCreate):
    """Update an existing episode profile"""
    try:
        profile = await EpisodeProfile.get(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Episode profile '{profile_id}' not found"
            )
        
        # Update fields
        profile.name = profile_data.name
        profile.description = profile_data.description
        profile.speaker_config = profile_data.speaker_config
        profile.outline_provider = profile_data.outline_provider
        profile.outline_model = profile_data.outline_model
        profile.transcript_provider = profile_data.transcript_provider
        profile.transcript_model = profile_data.transcript_model
        profile.default_briefing = profile_data.default_briefing
        profile.num_segments = profile_data.num_segments
        
        await profile.save()
        
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
        logger.error(f"Failed to update episode profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update episode profile: {str(e)}"
        )


@router.delete("/episode-profiles/{profile_id}")
async def delete_episode_profile(profile_id: str):
    """Delete an episode profile"""
    try:
        profile = await EpisodeProfile.get(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Episode profile '{profile_id}' not found"
            )
        
        await profile.delete()
        
        return {"message": "Episode profile deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete episode profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete episode profile: {str(e)}"
        )


@router.post("/episode-profiles/{profile_id}/duplicate", response_model=EpisodeProfileResponse)
async def duplicate_episode_profile(profile_id: str):
    """Duplicate an episode profile"""
    try:
        original = await EpisodeProfile.get(profile_id)
        
        if not original:
            raise HTTPException(
                status_code=404,
                detail=f"Episode profile '{profile_id}' not found"
            )
        
        # Create duplicate with modified name
        duplicate = EpisodeProfile(
            name=f"{original.name} - Copy",
            description=original.description,
            speaker_config=original.speaker_config,
            outline_provider=original.outline_provider,
            outline_model=original.outline_model,
            transcript_provider=original.transcript_provider,
            transcript_model=original.transcript_model,
            default_briefing=original.default_briefing,
            num_segments=original.num_segments
        )
        
        await duplicate.save()
        
        return EpisodeProfileResponse(
            id=str(duplicate.id),
            name=duplicate.name,
            description=duplicate.description or "",
            speaker_config=duplicate.speaker_config,
            outline_provider=duplicate.outline_provider,
            outline_model=duplicate.outline_model,
            transcript_provider=duplicate.transcript_provider,
            transcript_model=duplicate.transcript_model,
            default_briefing=duplicate.default_briefing,
            num_segments=duplicate.num_segments
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate episode profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to duplicate episode profile: {str(e)}"
        )