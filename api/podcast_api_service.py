"""
Podcast service layer using API client.
This replaces direct httpx calls in the Streamlit pages.
"""

from typing import Any, Dict, List

from loguru import logger

from api.client import api_client


class PodcastAPIService:
    """Service layer for podcast operations using API client."""

    def __init__(self):
        logger.info("Using API client for podcast operations")

    # Episode methods
    def get_episodes(self) -> List[Dict[Any, Any]]:
        """Get all podcast episodes."""
        result = api_client._make_request("GET", "/api/podcasts/episodes")
        return result if isinstance(result, list) else [result]

    def delete_episode(self, episode_id: str) -> bool:
        """Delete a podcast episode."""
        try:
            api_client._make_request("DELETE", f"/api/podcasts/episodes/{episode_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete episode: {e}")
            return False

    # Episode Profile methods
    def get_episode_profiles(self) -> List[Dict]:
        """Get all episode profiles."""
        return api_client.get_episode_profiles()

    def create_episode_profile(self, profile_data: Dict) -> bool:
        """Create a new episode profile."""
        try:
            api_client.create_episode_profile(**profile_data)
            return True
        except Exception as e:
            logger.error(f"Failed to create episode profile: {e}")
            return False

    def update_episode_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Update an episode profile."""
        try:
            api_client.update_episode_profile(profile_id, **profile_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update episode profile: {e}")
            return False

    def delete_episode_profile(self, profile_id: str) -> bool:
        """Delete an episode profile."""
        try:
            api_client.delete_episode_profile(profile_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete episode profile: {e}")
            return False

    def duplicate_episode_profile(self, profile_id: str) -> bool:
        """Duplicate an episode profile."""
        try:
            api_client._make_request(
                "POST", f"/api/episode-profiles/{profile_id}/duplicate"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to duplicate episode profile: {e}")
            return False

    # Speaker Profile methods
    def get_speaker_profiles(self) -> List[Dict[Any, Any]]:
        """Get all speaker profiles."""
        result = api_client._make_request("GET", "/api/speaker-profiles")
        return result if isinstance(result, list) else [result]

    def create_speaker_profile(self, profile_data: Dict) -> bool:
        """Create a new speaker profile."""
        try:
            api_client._make_request("POST", "/api/speaker-profiles", json=profile_data)
            return True
        except Exception as e:
            logger.error(f"Failed to create speaker profile: {e}")
            return False

    def update_speaker_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Update a speaker profile."""
        try:
            api_client._make_request(
                "PUT", f"/api/speaker-profiles/{profile_id}", json=profile_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update speaker profile: {e}")
            return False

    def delete_speaker_profile(self, profile_id: str) -> bool:
        """Delete a speaker profile."""
        try:
            api_client._make_request("DELETE", f"/api/speaker-profiles/{profile_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete speaker profile: {e}")
            return False

    def duplicate_speaker_profile(self, profile_id: str) -> bool:
        """Duplicate a speaker profile."""
        try:
            api_client._make_request(
                "POST", f"/api/speaker-profiles/{profile_id}/duplicate"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to duplicate speaker profile: {e}")
            return False


# Global service instance
podcast_api_service = PodcastAPIService()
