from typing import Any, Dict, Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from surreal_commands import get_command_status, submit_command

from open_notebook.domain.notebook import Notebook
from open_notebook.domain.podcast import EpisodeProfile, PodcastEpisode, SpeakerProfile


class PodcastGenerationRequest(BaseModel):
    """Request model for podcast generation"""

    episode_profile: str
    speaker_profile: str
    episode_name: str
    content: Optional[str] = None
    notebook_id: Optional[str] = None
    briefing_suffix: Optional[str] = None


class PodcastGenerationResponse(BaseModel):
    """Response model for podcast generation"""

    job_id: str
    status: str
    message: str
    episode_profile: str
    episode_name: str


class PodcastService:
    """Service layer for podcast operations"""

    @staticmethod
    async def submit_generation_job(
        episode_profile_name: str,
        speaker_profile_name: str,
        episode_name: str,
        notebook_id: Optional[str] = None,
        content: Optional[str] = None,
        briefing_suffix: Optional[str] = None,
    ) -> str:
        """Submit a podcast generation job for background processing"""
        try:
            # Validate episode profile exists
            episode_profile = await EpisodeProfile.get_by_name(episode_profile_name)
            if not episode_profile:
                raise ValueError(f"Episode profile '{episode_profile_name}' not found")

            # Validate speaker profile exists
            speaker_profile = await SpeakerProfile.get_by_name(speaker_profile_name)
            if not speaker_profile:
                raise ValueError(f"Speaker profile '{speaker_profile_name}' not found")

            # Get content from notebook if not provided directly
            if not content and notebook_id:
                try:
                    notebook = await Notebook.get(notebook_id)
                    # Get notebook context (this may need to be adjusted based on actual Notebook implementation)
                    content = (
                        await notebook.get_context()
                        if hasattr(notebook, "get_context")
                        else str(notebook)
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get notebook content, using notebook_id as content: {e}"
                    )
                    content = f"Notebook ID: {notebook_id}"

            if not content:
                raise ValueError(
                    "Content is required - provide either content or notebook_id"
                )

            # Prepare command arguments
            command_args = {
                "episode_profile": episode_profile_name,
                "speaker_profile": speaker_profile_name,
                "episode_name": episode_name,
                "content": str(content),
                "briefing_suffix": briefing_suffix,
            }

            # Ensure command modules are imported before submitting
            # This is needed because submit_command validates against local registry
            try:
                import commands.podcast_commands  # noqa: F401
            except ImportError as import_err:
                logger.error(f"Failed to import podcast commands: {import_err}")
                raise ValueError("Podcast commands not available")

            # Submit command to surreal-commands
            job_id = submit_command("open_notebook", "generate_podcast", command_args)

            # Convert RecordID to string if needed
            if not job_id:
                raise ValueError("Failed to get job_id from submit_command")
            job_id_str = str(job_id)
            logger.info(
                f"Submitted podcast generation job: {job_id_str} for episode '{episode_name}'"
            )
            return job_id_str

        except Exception as e:
            logger.error(f"Failed to submit podcast generation job: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit podcast generation job: {str(e)}",
            )

    @staticmethod
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get status of a podcast generation job"""
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status if status else "unknown",
                "result": status.result if status else None,
                "error_message": getattr(status, "error_message", None)
                if status
                else None,
                "created": str(status.created)
                if status and hasattr(status, "created") and status.created
                else None,
                "updated": str(status.updated)
                if status and hasattr(status, "updated") and status.updated
                else None,
                "progress": getattr(status, "progress", None) if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get podcast job status: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get job status: {str(e)}"
            )

    @staticmethod
    async def list_episodes() -> list:
        """List all podcast episodes"""
        try:
            episodes = await PodcastEpisode.get_all(order_by="created desc")
            return episodes
        except Exception as e:
            logger.error(f"Failed to list podcast episodes: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list episodes: {str(e)}"
            )

    @staticmethod
    async def get_episode(episode_id: str) -> PodcastEpisode:
        """Get a specific podcast episode"""
        try:
            episode = await PodcastEpisode.get(episode_id)
            return episode
        except Exception as e:
            logger.error(f"Failed to get podcast episode {episode_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Episode not found: {str(e)}")


class DefaultProfiles:
    """Utility class for creating default profiles (if needed beyond migration data)"""

    @staticmethod
    async def create_default_episode_profiles():
        """Create default episode profiles if they don't exist"""
        try:
            # Check if profiles already exist
            existing = await EpisodeProfile.get_all()
            if existing:
                logger.info(f"Episode profiles already exist: {len(existing)} found")
                return existing

            # This would create profiles, but since we have migration data,
            # this is mainly for future extensibility
            logger.info(
                "Default episode profiles should be created via database migration"
            )
            return []

        except Exception as e:
            logger.error(f"Failed to create default episode profiles: {e}")
            raise

    @staticmethod
    async def create_default_speaker_profiles():
        """Create default speaker profiles if they don't exist"""
        try:
            # Check if profiles already exist
            existing = await SpeakerProfile.get_all()
            if existing:
                logger.info(f"Speaker profiles already exist: {len(existing)} found")
                return existing

            # This would create profiles, but since we have migration data,
            # this is mainly for future extensibility
            logger.info(
                "Default speaker profiles should be created via database migration"
            )
            return []

        except Exception as e:
            logger.error(f"Failed to create default speaker profiles: {e}")
            raise
