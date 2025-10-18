from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.domain.podcast import SpeakerProfile

router = APIRouter()


class SpeakerProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    tts_provider: str
    tts_model: str
    speakers: List[Dict[str, Any]]


@router.get("/speaker-profiles", response_model=List[SpeakerProfileResponse])
async def list_speaker_profiles():
    """List all available speaker profiles"""
    try:
        profiles = await SpeakerProfile.get_all(order_by="name asc")
        
        return [
            SpeakerProfileResponse(
                id=str(profile.id),
                name=profile.name,
                description=profile.description or "",
                tts_provider=profile.tts_provider,
                tts_model=profile.tts_model,
                speakers=profile.speakers
            )
            for profile in profiles
        ]
        
    except Exception as e:
        logger.error(f"Failed to fetch speaker profiles: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch speaker profiles: {str(e)}"
        )


@router.get("/speaker-profiles/{profile_name}", response_model=SpeakerProfileResponse)
async def get_speaker_profile(profile_name: str):
    """Get a specific speaker profile by name"""
    try:
        profile = await SpeakerProfile.get_by_name(profile_name)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Speaker profile '{profile_name}' not found"
            )
        
        return SpeakerProfileResponse(
            id=str(profile.id),
            name=profile.name,
            description=profile.description or "",
            tts_provider=profile.tts_provider,
            tts_model=profile.tts_model,
            speakers=profile.speakers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch speaker profile '{profile_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch speaker profile: {str(e)}"
        )


class SpeakerProfileCreate(BaseModel):
    name: str = Field(..., description="Unique profile name")
    description: str = Field("", description="Profile description")
    tts_provider: str = Field(..., description="TTS provider")
    tts_model: str = Field(..., description="TTS model name")
    speakers: List[Dict[str, Any]] = Field(..., description="Array of speaker configurations")


@router.post("/speaker-profiles", response_model=SpeakerProfileResponse)
async def create_speaker_profile(profile_data: SpeakerProfileCreate):
    """Create a new speaker profile"""
    try:
        profile = SpeakerProfile(
            name=profile_data.name,
            description=profile_data.description,
            tts_provider=profile_data.tts_provider,
            tts_model=profile_data.tts_model,
            speakers=profile_data.speakers
        )
        
        await profile.save()
        
        return SpeakerProfileResponse(
            id=str(profile.id),
            name=profile.name,
            description=profile.description or "",
            tts_provider=profile.tts_provider,
            tts_model=profile.tts_model,
            speakers=profile.speakers
        )
        
    except Exception as e:
        logger.error(f"Failed to create speaker profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create speaker profile: {str(e)}"
        )


@router.put("/speaker-profiles/{profile_id}", response_model=SpeakerProfileResponse)
async def update_speaker_profile(profile_id: str, profile_data: SpeakerProfileCreate):
    """Update an existing speaker profile"""
    try:
        profile = await SpeakerProfile.get(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Speaker profile '{profile_id}' not found"
            )
        
        # Update fields
        profile.name = profile_data.name
        profile.description = profile_data.description
        profile.tts_provider = profile_data.tts_provider
        profile.tts_model = profile_data.tts_model
        profile.speakers = profile_data.speakers
        
        await profile.save()
        
        return SpeakerProfileResponse(
            id=str(profile.id),
            name=profile.name,
            description=profile.description or "",
            tts_provider=profile.tts_provider,
            tts_model=profile.tts_model,
            speakers=profile.speakers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update speaker profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update speaker profile: {str(e)}"
        )


@router.delete("/speaker-profiles/{profile_id}")
async def delete_speaker_profile(profile_id: str):
    """Delete a speaker profile"""
    try:
        profile = await SpeakerProfile.get(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Speaker profile '{profile_id}' not found"
            )
        
        await profile.delete()
        
        return {"message": "Speaker profile deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete speaker profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete speaker profile: {str(e)}"
        )


@router.post("/speaker-profiles/{profile_id}/duplicate", response_model=SpeakerProfileResponse)
async def duplicate_speaker_profile(profile_id: str):
    """Duplicate a speaker profile"""
    try:
        original = await SpeakerProfile.get(profile_id)
        
        if not original:
            raise HTTPException(
                status_code=404,
                detail=f"Speaker profile '{profile_id}' not found"
            )
        
        # Create duplicate with modified name
        duplicate = SpeakerProfile(
            name=f"{original.name} - Copy",
            description=original.description,
            tts_provider=original.tts_provider,
            tts_model=original.tts_model,
            speakers=original.speakers
        )
        
        await duplicate.save()
        
        return SpeakerProfileResponse(
            id=str(duplicate.id),
            name=duplicate.name,
            description=duplicate.description or "",
            tts_provider=duplicate.tts_provider,
            tts_model=duplicate.tts_model,
            speakers=duplicate.speakers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate speaker profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to duplicate speaker profile: {str(e)}"
        )