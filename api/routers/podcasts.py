from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, unquote, urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from api.podcast_service import (
    PodcastGenerationRequest,
    PodcastGenerationResponse,
    PodcastService,
)
from api.video_service import (
    EpisodeVideoGenerationRequest,
    EpisodeVideoGenerationResponse,
    StoryboardItemPatchRequest,
    VideoService,
)

router = APIRouter()


class PodcastEpisodeResponse(BaseModel):
    id: str
    name: str
    episode_profile: dict
    speaker_profile: dict
    briefing: str
    audio_file: Optional[str] = None
    audio_url: Optional[str] = None
    transcript: Optional[dict] = None
    outline: Optional[dict] = None
    created: Optional[str] = None
    job_status: Optional[str] = None
    error_message: Optional[str] = None


class EpisodeVideoResponse(BaseModel):
    id: str
    name: str
    episode: str
    status: str
    video_file: Optional[str] = None
    video_url: Optional[str] = None
    storyboard: Optional[dict] = None
    assets: list = []
    settings: dict = {}
    usage: Optional[dict] = None
    error_message: Optional[str] = None
    created: Optional[str] = None


def _resolve_audio_path(audio_file: str) -> Path:
    if audio_file.startswith("file://"):
        parsed = urlparse(audio_file)
        return Path(unquote(parsed.path))
    return Path(audio_file)


def _resolve_file_path(file_path: str) -> Path:
    return _resolve_audio_path(file_path)


def _asset_to_response(video, asset: dict) -> dict:
    response = dict(asset)
    asset_id = response.get("id")
    asset_path = response.get("path")
    if asset_id and asset_path and _resolve_file_path(asset_path).exists():
        response["file_url"] = (
            f"/api/podcasts/videos/{quote(str(video.id), safe='')}"
            f"/assets/{quote(str(asset_id), safe='')}/file"
        )
    return response


def _video_to_response(video) -> EpisodeVideoResponse:
    video_url = None
    if video.video_file:
        video_path = _resolve_file_path(video.video_file)
        if video_path.exists():
            video_url = f"/api/podcasts/videos/{quote(str(video.id), safe='')}/file"
    return EpisodeVideoResponse(
        id=str(video.id),
        name=video.name,
        episode=str(video.episode),
        status=video.status,
        video_file=video.video_file,
        video_url=video_url,
        storyboard=video.storyboard,
        assets=[_asset_to_response(video, asset) for asset in video.assets],
        settings=video.settings,
        usage=video.usage,
        error_message=video.error_message,
        created=str(video.created) if video.created else None,
    )


@router.post("/podcasts/generate", response_model=PodcastGenerationResponse)
async def generate_podcast(request: PodcastGenerationRequest):
    """
    Generate a podcast episode using Episode Profiles.
    Returns immediately with job ID for status tracking.
    """
    try:
        job_id = await PodcastService.submit_generation_job(
            episode_profile_name=request.episode_profile,
            speaker_profile_name=request.speaker_profile,
            episode_name=request.episode_name,
            notebook_id=request.notebook_id,
            content=request.content,
            briefing_suffix=request.briefing_suffix,
        )

        return PodcastGenerationResponse(
            job_id=job_id,
            status="submitted",
            message=f"Podcast generation started for episode '{request.episode_name}'",
            episode_profile=request.episode_profile,
            episode_name=request.episode_name,
        )

    except Exception as e:
        logger.error(f"Error generating podcast: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate podcast")


@router.get("/podcasts/jobs/{job_id}")
async def get_podcast_job_status(job_id: str):
    """Get the status of a podcast generation job"""
    try:
        status_data = await PodcastService.get_job_status(job_id)
        return status_data

    except Exception as e:
        logger.error(f"Error fetching podcast job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.post(
    "/podcasts/episodes/{episode_id}/video",
    response_model=EpisodeVideoGenerationResponse,
)
async def generate_episode_video(
    episode_id: str,
    request: EpisodeVideoGenerationRequest,
):
    """Generate a storyboard video for an existing podcast episode."""
    job_id = await VideoService.submit_generation_job(episode_id, request)
    return EpisodeVideoGenerationResponse(
        job_id=job_id,
        status="submitted",
        message=f"Video generation started for episode '{episode_id}'",
    )


@router.get("/podcasts/video-presets")
async def list_episode_video_presets():
    """List available codex-configurable video style presets."""
    return VideoService.list_presets()


@router.get("/podcasts/videos/jobs/{job_id}")
async def get_episode_video_job_status(job_id: str):
    """Get the status of a video generation job."""
    return await VideoService.get_job_status(job_id)


@router.get(
    "/podcasts/episodes/{episode_id}/videos",
    response_model=List[EpisodeVideoResponse],
)
async def list_episode_videos(episode_id: str):
    """List generated videos for a podcast episode."""
    videos = await VideoService.list_for_episode(episode_id)
    return [_video_to_response(video) for video in videos]


@router.get("/podcasts/videos/{video_id}", response_model=EpisodeVideoResponse)
async def get_episode_video(video_id: str):
    """Get a generated episode video artifact."""
    video = await VideoService.get(video_id)
    return _video_to_response(video)


@router.get("/podcasts/videos/{video_id}/file")
async def stream_episode_video_file(video_id: str):
    """Stream the MP4 file associated with an episode video."""
    video = await VideoService.get(video_id)
    if not video.video_file:
        raise HTTPException(status_code=404, detail="Video has no rendered file")
    video_path = _resolve_file_path(video.video_file)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)


@router.get("/podcasts/videos/{video_id}/assets/{asset_id}/file")
@router.get("/podcasts/videos/{video_id}/assets/{asset_id}")
async def stream_episode_video_asset_file(video_id: str, asset_id: str):
    """Stream a generated image asset associated with an episode video."""
    video = await VideoService.get(video_id)
    candidate_ids = {asset_id}
    if asset_id.endswith(".png"):
        candidate_ids.add(asset_id[:-4])

    def matches_requested_asset(item: dict) -> bool:
        return (
            item.get("id") in candidate_ids
            or Path(item.get("path", "")).name == asset_id
        )

    asset = next((item for item in video.assets if matches_requested_asset(item)), None)
    if not asset or not asset.get("path"):
        raise HTTPException(status_code=404, detail="Video asset not found")

    asset_path = _resolve_file_path(asset["path"])
    if not asset_path.exists():
        raise HTTPException(
            status_code=404, detail="Video asset file not found on disk"
        )

    suffix = asset_path.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return FileResponse(asset_path, media_type=media_type, filename=asset_path.name)


@router.patch(
    "/podcasts/videos/{video_id}/storyboard/items/{item_id}",
    response_model=EpisodeVideoResponse,
)
async def patch_episode_video_storyboard_item(
    video_id: str,
    item_id: str,
    request: StoryboardItemPatchRequest,
):
    """Patch a single storyboard item. Regenerate its asset before rendering."""
    video = await VideoService.patch_item(video_id, item_id, request)
    return _video_to_response(video)


@router.post(
    "/podcasts/videos/{video_id}/storyboard/items/{item_id}/regenerate",
    response_model=EpisodeVideoResponse,
)
async def regenerate_episode_video_storyboard_item(video_id: str, item_id: str):
    """Regenerate one scene image asset from the current storyboard prompt."""
    video = await VideoService.regenerate_item(video_id, item_id)
    return _video_to_response(video)


@router.post("/podcasts/videos/{video_id}/render", response_model=EpisodeVideoResponse)
async def render_episode_video(video_id: str):
    """Rerender an MP4 from the current storyboard assets and source audio."""
    video = await VideoService.render(video_id)
    return _video_to_response(video)


@router.get("/podcasts/episodes", response_model=List[PodcastEpisodeResponse])
async def list_podcast_episodes():
    """List all podcast episodes"""
    try:
        episodes = await PodcastService.list_episodes()

        response_episodes = []
        for episode in episodes:
            # Skip incomplete episodes without command or audio
            if not episode.command and not episode.audio_file:
                continue

            # Get job status and error message if available
            job_status = None
            error_message = None
            if episode.command:
                try:
                    detail = await episode.get_job_detail()
                    job_status = detail["status"]
                    error_message = detail["error_message"]
                except Exception:
                    job_status = "unknown"
            else:
                # No command but has audio file = completed import
                job_status = "completed"

            audio_url = None
            if episode.audio_file:
                audio_path = _resolve_audio_path(episode.audio_file)
                if audio_path.exists():
                    audio_url = f"/api/podcasts/episodes/{episode.id}/audio"

            response_episodes.append(
                PodcastEpisodeResponse(
                    id=str(episode.id),
                    name=episode.name,
                    episode_profile=episode.episode_profile,
                    speaker_profile=episode.speaker_profile,
                    briefing=episode.briefing,
                    audio_file=episode.audio_file,
                    audio_url=audio_url,
                    transcript=episode.transcript,
                    outline=episode.outline,
                    created=str(episode.created) if episode.created else None,
                    job_status=job_status,
                    error_message=error_message,
                )
            )

        return response_episodes

    except Exception as e:
        logger.error(f"Error listing podcast episodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list podcast episodes")


@router.get("/podcasts/episodes/{episode_id}", response_model=PodcastEpisodeResponse)
async def get_podcast_episode(episode_id: str):
    """Get a specific podcast episode"""
    try:
        episode = await PodcastService.get_episode(episode_id)

        # Get job status and error message if available
        job_status = None
        error_message = None
        if episode.command:
            try:
                detail = await episode.get_job_detail()
                job_status = detail["status"]
                error_message = detail["error_message"]
            except Exception:
                job_status = "unknown"
        else:
            # No command but has audio file = completed import
            job_status = "completed" if episode.audio_file else "unknown"

        audio_url = None
        if episode.audio_file:
            audio_path = _resolve_audio_path(episode.audio_file)
            if audio_path.exists():
                audio_url = f"/api/podcasts/episodes/{episode.id}/audio"

        return PodcastEpisodeResponse(
            id=str(episode.id),
            name=episode.name,
            episode_profile=episode.episode_profile,
            speaker_profile=episode.speaker_profile,
            briefing=episode.briefing,
            audio_file=episode.audio_file,
            audio_url=audio_url,
            transcript=episode.transcript,
            outline=episode.outline,
            created=str(episode.created) if episode.created else None,
            job_status=job_status,
            error_message=error_message,
        )

    except Exception as e:
        logger.error(f"Error fetching podcast episode: {str(e)}")
        raise HTTPException(status_code=404, detail="Episode not found")


@router.get("/podcasts/episodes/{episode_id}/audio")
async def stream_podcast_episode_audio(episode_id: str):
    """Stream the audio file associated with a podcast episode"""
    try:
        episode = await PodcastService.get_episode(episode_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching podcast episode for audio: {str(e)}")
        raise HTTPException(status_code=404, detail="Episode not found")

    if not episode.audio_file:
        raise HTTPException(status_code=404, detail="Episode has no audio file")

    audio_path = _resolve_audio_path(episode.audio_file)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=audio_path.name,
    )


@router.post("/podcasts/episodes/{episode_id}/retry")
async def retry_podcast_episode(episode_id: str):
    """Retry a failed podcast episode by deleting it and submitting a new job"""
    try:
        episode = await PodcastService.get_episode(episode_id)

        # Validate episode is in a failed state
        detail = await episode.get_job_detail()
        if detail["status"] not in ("failed", "error"):
            raise HTTPException(
                status_code=400,
                detail=f"Episode is not in a failed state (current: {detail['status']})",
            )

        # Extract params for re-submission
        ep_profile_name = episode.episode_profile.get("name")
        sp_profile_name = episode.speaker_profile.get("name")
        episode_name = episode.name
        content = episode.content

        if not ep_profile_name or not sp_profile_name:
            raise HTTPException(
                status_code=400,
                detail="Cannot retry: episode or speaker profile name missing from stored data",
            )

        # Delete audio file if any
        if episode.audio_file:
            audio_path = _resolve_audio_path(episode.audio_file)
            if audio_path.exists():
                try:
                    audio_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path}: {e}")

        # Delete the failed episode
        await episode.delete()

        # Submit a new job
        job_id = await PodcastService.submit_generation_job(
            episode_profile_name=ep_profile_name,
            speaker_profile_name=sp_profile_name,
            episode_name=episode_name,
            content=content,
        )

        return {"job_id": job_id, "message": "Retry submitted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying podcast episode: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retry episode")


@router.delete("/podcasts/episodes/{episode_id}")
async def delete_podcast_episode(episode_id: str):
    """Delete a podcast episode and its associated audio file"""
    try:
        # Get the episode first to check if it exists and get the audio file path
        episode = await PodcastService.get_episode(episode_id)

        # Delete the physical audio file if it exists
        if episode.audio_file:
            audio_path = _resolve_audio_path(episode.audio_file)
            if audio_path.exists():
                try:
                    audio_path.unlink()
                    logger.info(f"Deleted audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path}: {e}")

        # Delete the episode from the database
        await episode.delete()

        logger.info(f"Deleted podcast episode: {episode_id}")
        return {"message": "Episode deleted successfully", "episode_id": episode_id}

    except Exception as e:
        logger.error(f"Error deleting podcast episode: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete episode")
