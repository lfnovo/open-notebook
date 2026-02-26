from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.podcasts.models import SpeakerProfile

router = APIRouter()


class SpeakerProfileResponse(BaseModel):
    id: str
    name: str
    description: str
    voice_model: Optional[str] = None
    speakers: List[Dict[str, Any]]
    # Legacy fields (for display/migration awareness)
    tts_provider: Optional[str] = None
    tts_model: Optional[str] = None


def _profile_to_response(profile: SpeakerProfile) -> SpeakerProfileResponse:
    return SpeakerProfileResponse(
        id=str(profile.id),
        name=profile.name,
        description=profile.description or "",
        voice_model=profile.voice_model,
        speakers=profile.speakers,
        tts_provider=profile.tts_provider,
        tts_model=profile.tts_model,
    )


@router.get("/speaker-profiles", response_model=List[SpeakerProfileResponse])
async def list_speaker_profiles():
    """List all available speaker profiles"""
    try:
        profiles = await SpeakerProfile.get_all(order_by="name asc")
        return [_profile_to_response(p) for p in profiles]
    except Exception as e:
        logger.error(f"Failed to fetch speaker profiles: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch speaker profiles"
        )


@router.get("/speaker-profiles/{profile_name}", response_model=SpeakerProfileResponse)
async def get_speaker_profile(profile_name: str):
    """Get a specific speaker profile by name"""
    try:
        profile = await SpeakerProfile.get_by_name(profile_name)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Speaker profile '{profile_name}' not found"
            )

        return _profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch speaker profile '{profile_name}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch speaker profile"
        )


class SpeakerProfileCreate(BaseModel):
    name: str = Field(..., description="Unique profile name")
    description: str = Field("", description="Profile description")
    voice_model: Optional[str] = Field(None, description="Model record ID for TTS")
    speakers: List[Dict[str, Any]] = Field(
        ..., description="Array of speaker configurations"
    )
    # Legacy fields (accepted but not required)
    tts_provider: Optional[str] = None
    tts_model: Optional[str] = None


@router.post("/speaker-profiles", response_model=SpeakerProfileResponse)
async def create_speaker_profile(profile_data: SpeakerProfileCreate):
    """Create a new speaker profile"""
    try:
        profile = SpeakerProfile(
            name=profile_data.name,
            description=profile_data.description,
            voice_model=profile_data.voice_model,
            speakers=profile_data.speakers,
            tts_provider=profile_data.tts_provider,
            tts_model=profile_data.tts_model,
        )

        await profile.save()
        return _profile_to_response(profile)

    except Exception as e:
        logger.error(f"Failed to create speaker profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create speaker profile"
        )


@router.put("/speaker-profiles/{profile_id}", response_model=SpeakerProfileResponse)
async def update_speaker_profile(profile_id: str, profile_data: SpeakerProfileCreate):
    """Update an existing speaker profile"""
    try:
        profile = await SpeakerProfile.get(profile_id)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Speaker profile '{profile_id}' not found"
            )

        profile.name = profile_data.name
        profile.description = profile_data.description
        profile.voice_model = profile_data.voice_model
        profile.speakers = profile_data.speakers
        profile.tts_provider = profile_data.tts_provider
        profile.tts_model = profile_data.tts_model

        await profile.save()
        return _profile_to_response(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update speaker profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update speaker profile"
        )


@router.delete("/speaker-profiles/{profile_id}")
async def delete_speaker_profile(profile_id: str):
    """Delete a speaker profile"""
    try:
        profile = await SpeakerProfile.get(profile_id)

        if not profile:
            raise HTTPException(
                status_code=404, detail=f"Speaker profile '{profile_id}' not found"
            )

        await profile.delete()

        return {"message": "Speaker profile deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete speaker profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete speaker profile"
        )


@router.post(
    "/speaker-profiles/{profile_id}/duplicate", response_model=SpeakerProfileResponse
)
async def duplicate_speaker_profile(profile_id: str):
    """Duplicate a speaker profile"""
    try:
        original = await SpeakerProfile.get(profile_id)

        if not original:
            raise HTTPException(
                status_code=404, detail=f"Speaker profile '{profile_id}' not found"
            )

        duplicate = SpeakerProfile(
            name=f"{original.name} - Copy",
            description=original.description,
            voice_model=original.voice_model,
            speakers=original.speakers,
            tts_provider=original.tts_provider,
            tts_model=original.tts_model,
        )

        await duplicate.save()
        return _profile_to_response(duplicate)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate speaker profile: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to duplicate speaker profile"
        )
