from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

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