from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from surreal_commands import get_command_status, submit_command

from open_notebook.podcasts.models import EpisodeVideo, PodcastEpisode
from open_notebook.podcasts.video_generation import (
    generate_scene_assets,
    get_episode_video,
    list_episode_videos,
    patch_storyboard_item,
    render_video_from_storyboard,
)
from open_notebook.podcasts.video_presets import (
    DEFAULT_VIDEO_STYLE_PRESET,
    list_video_style_presets,
)


class EpisodeVideoGenerationRequest(BaseModel):
    name: Optional[str] = None
    briefing: Optional[str] = None
    language_model_id: Optional[str] = None
    image_model_id: Optional[str] = None
    style_preset: str = DEFAULT_VIDEO_STYLE_PRESET
    aspect_ratio: str = "16:9"
    scene_density: str = "balanced"


class EpisodeVideoGenerationResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StoryboardItemPatchRequest(BaseModel):
    title: Optional[str] = None
    visual_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    slide_type: Optional[str] = None
    narration_summary: Optional[str] = None
    learning_intent: Optional[str] = None
    visual_concept: Optional[str] = None
    text_strategy: Optional[str] = None
    exact_text: Optional[List[str]] = None
    visual_instruction: Optional[str] = None
    duration: Optional[float] = None


class VideoService:
    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        return list_video_style_presets()

    @staticmethod
    async def submit_generation_job(
        episode_id: str,
        request: EpisodeVideoGenerationRequest,
    ) -> str:
        try:
            await PodcastEpisode.get(episode_id)
            try:
                import commands.video_commands  # noqa: F401
            except ImportError as import_err:
                logger.error(f"Failed to import video commands: {import_err}")
                raise ValueError("Video commands not available")

            command_args = {
                "episode_id": episode_id,
                "name": request.name,
                "briefing": request.briefing,
                "language_model_id": request.language_model_id,
                "image_model_id": request.image_model_id,
                "style_preset": request.style_preset,
                "aspect_ratio": request.aspect_ratio,
                "scene_density": request.scene_density,
            }
            job_id = submit_command("open_notebook", "generate_episode_video", command_args)
            if not job_id:
                raise ValueError("Failed to get job_id from submit_command")
            return str(job_id)
        except Exception as e:
            logger.error(f"Failed to submit video generation job: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit video generation job: {str(e)}",
            )

    @staticmethod
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status if status else "unknown",
                "result": status.result if status else None,
                "error_message": getattr(status, "error_message", None)
                if status
                else None,
                "progress": getattr(status, "progress", None) if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get video job status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def list_for_episode(episode_id: str) -> List[EpisodeVideo]:
        try:
            return await list_episode_videos(episode_id)
        except Exception as e:
            logger.error(f"Failed to list episode videos: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get(video_id: str) -> EpisodeVideo:
        try:
            return await get_episode_video(video_id)
        except Exception as e:
            logger.error(f"Failed to get episode video {video_id}: {e}")
            raise HTTPException(status_code=404, detail="Video not found")

    @staticmethod
    async def patch_item(
        video_id: str, item_id: str, patch: StoryboardItemPatchRequest
    ) -> EpisodeVideo:
        try:
            return await patch_storyboard_item(
                video_id, item_id, patch.model_dump(exclude_none=True)
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to patch storyboard item: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def regenerate_item(video_id: str, item_id: str) -> EpisodeVideo:
        try:
            video = await get_episode_video(video_id)
            output_dir_raw = video.settings.get("output_dir")
            output_dir = Path(output_dir_raw) if output_dir_raw else None
            if output_dir is None:
                video_file = Path(video.video_file) if video.video_file else None
                output_dir = video_file.parents[1] if video_file else None
            if output_dir is None:
                raise ValueError("Cannot resolve video output directory")
            item = next(
                item
                for item in video.storyboard.get("items", [])
                if item.get("id") == item_id
            )
            assets, usage = await generate_scene_assets(
                storyboard={"items": [item], "canvas": video.storyboard.get("canvas")},
                output_dir=output_dir,
                image_model_id=video.settings.get("image_model_id"),
            )
            video.assets = [
                asset for asset in video.assets if asset.get("id") != assets[0].get("id")
            ] + assets
            video.usage = video.usage or {}
            video.usage.setdefault("image_generation", [])
            video.usage["image_generation"].extend(usage.get("image_generation", []))
            video.status = "assets_ready"
            await video.save()
            return video
        except StopIteration:
            raise HTTPException(status_code=404, detail="Storyboard item not found")
        except Exception as e:
            logger.error(f"Failed to regenerate storyboard item: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def render(video_id: str) -> EpisodeVideo:
        try:
            video = await get_episode_video(video_id)
            episode = await PodcastEpisode.get(str(video.episode))
            if video.video_file:
                output_dir = Path(video.video_file).parents[1]
            elif video.assets:
                output_dir = Path(video.assets[0]["path"]).parents[1]
            else:
                raise ValueError("Video has no assets to render")
            video.video_file = render_video_from_storyboard(
                episode=episode,
                storyboard=video.storyboard,
                output_dir=output_dir,
            )
            video.status = "completed"
            video.error_message = None
            await video.save()
            return video
        except Exception as e:
            logger.error(f"Failed to render episode video: {e}")
            raise HTTPException(status_code=500, detail=str(e))
