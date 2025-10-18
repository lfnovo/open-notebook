"""
Episode profiles service layer using API.
"""

from typing import List

from loguru import logger

from api.client import api_client
from open_notebook.domain.podcast import EpisodeProfile


class EpisodeProfilesService:
    """Service layer for episode profiles operations using API."""
    
    def __init__(self):
        logger.info("Using API for episode profiles operations")
    
    def get_all_episode_profiles(self) -> List[EpisodeProfile]:
        """Get all episode profiles."""
        profiles_data = api_client.get_episode_profiles()
        # Convert API response to EpisodeProfile objects
        profiles = []
        for profile_data in profiles_data:
            profile = EpisodeProfile(
                name=profile_data["name"],
                description=profile_data.get("description", ""),
                speaker_config=profile_data["speaker_config"],
                outline_provider=profile_data["outline_provider"],
                outline_model=profile_data["outline_model"],
                transcript_provider=profile_data["transcript_provider"],
                transcript_model=profile_data["transcript_model"],
                default_briefing=profile_data["default_briefing"],
                num_segments=profile_data["num_segments"]
            )
            profile.id = profile_data["id"]
            profiles.append(profile)
        return profiles
    
    def get_episode_profile(self, profile_name: str) -> EpisodeProfile:
        """Get a specific episode profile by name."""
        profile_response = api_client.get_episode_profile(profile_name)
        profile_data = profile_response if isinstance(profile_response, dict) else profile_response[0]
        profile = EpisodeProfile(
            name=profile_data["name"],
            description=profile_data.get("description", ""),
            speaker_config=profile_data["speaker_config"],
            outline_provider=profile_data["outline_provider"],
            outline_model=profile_data["outline_model"],
            transcript_provider=profile_data["transcript_provider"],
            transcript_model=profile_data["transcript_model"],
            default_briefing=profile_data["default_briefing"],
            num_segments=profile_data["num_segments"]
        )
        profile.id = profile_data["id"]
        return profile
    
    def create_episode_profile(
        self,
        name: str,
        description: str = "",
        speaker_config: str = "",
        outline_provider: str = "",
        outline_model: str = "",
        transcript_provider: str = "",
        transcript_model: str = "",
        default_briefing: str = "",
        num_segments: int = 5,
    ) -> EpisodeProfile:
        """Create a new episode profile."""
        profile_response = api_client.create_episode_profile(
            name=name,
            description=description,
            speaker_config=speaker_config,
            outline_provider=outline_provider,
            outline_model=outline_model,
            transcript_provider=transcript_provider,
            transcript_model=transcript_model,
            default_briefing=default_briefing,
            num_segments=num_segments,
        )
        profile_data = profile_response if isinstance(profile_response, dict) else profile_response[0]
        profile = EpisodeProfile(
            name=profile_data["name"],
            description=profile_data.get("description", ""),
            speaker_config=profile_data["speaker_config"],
            outline_provider=profile_data["outline_provider"],
            outline_model=profile_data["outline_model"],
            transcript_provider=profile_data["transcript_provider"],
            transcript_model=profile_data["transcript_model"],
            default_briefing=profile_data["default_briefing"],
            num_segments=profile_data["num_segments"]
        )
        profile.id = profile_data["id"]
        return profile
    
    def delete_episode_profile(self, profile_id: str) -> bool:
        """Delete an episode profile."""
        api_client.delete_episode_profile(profile_id)
        return True


# Global service instance
episode_profiles_service = EpisodeProfilesService()