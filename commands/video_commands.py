import json
import time
from pathlib import Path
from typing import Optional

from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id
from open_notebook.podcasts.models import EpisodeVideo, PodcastEpisode
from open_notebook.podcasts.video_generation import (
    DEFAULT_CANVAS,
    build_storyboard,
    build_video_output_dir,
    generate_scene_assets,
    render_video_from_storyboard,
)
from open_notebook.podcasts.video_presets import (
    DEFAULT_VIDEO_STYLE_PRESET,
    get_video_style_preset,
)


class EpisodeVideoGenerationInput(CommandInput):
    episode_id: str
    name: Optional[str] = None
    briefing: Optional[str] = None
    language_model_id: Optional[str] = None
    image_model_id: Optional[str] = None
    style_preset: str = DEFAULT_VIDEO_STYLE_PRESET
    aspect_ratio: str = "16:9"
    scene_density: str = "balanced"


class EpisodeVideoGenerationOutput(CommandOutput):
    success: bool
    video_id: Optional[str] = None
    video_file_path: Optional[str] = None
    storyboard_path: Optional[str] = None
    processing_time: float
    error_message: Optional[str] = None


@command("generate_episode_video", app="open_notebook", retry={"max_attempts": 1})
async def generate_episode_video_command(
    input_data: EpisodeVideoGenerationInput,
) -> EpisodeVideoGenerationOutput:
    start_time = time.time()
    video: Optional[EpisodeVideo] = None

    try:
        episode = await PodcastEpisode.get(input_data.episode_id)
        if not episode.audio_file:
            raise ValueError("Podcast episode has no audio file")
        if not episode.transcript:
            raise ValueError("Podcast episode has no transcript")

        video_dir_name, output_dir = build_video_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        style_preset = get_video_style_preset(input_data.style_preset)
        settings = {
            "style_preset": style_preset.name,
            "style_description": style_preset.description,
            "aspect_ratio": input_data.aspect_ratio,
            "scene_density": input_data.scene_density,
            "language_model_id": input_data.language_model_id,
            "image_model_id": input_data.image_model_id,
            "canvas": DEFAULT_CANVAS,
            "output_dir_name": video_dir_name,
            "output_dir": str(output_dir),
        }

        video = EpisodeVideo(
            name=input_data.name or f"{episode.name} video",
            episode=ensure_record_id(str(episode.id)),
            command=ensure_record_id(input_data.execution_context.command_id)
            if input_data.execution_context
            else None,
            status="running",
            video_file=None,
            storyboard={},
            assets=[],
            settings=settings,
            usage={},
            error_message=None,
        )
        await video.save()

        briefing = input_data.briefing or (
            "Создай чистое корпоративное обучающее видео по готовой аудиодорожке. "
            "Визуалы должны быть понятными, спокойными и практичными."
        )
        storyboard = await build_storyboard(
            episode=episode,
            briefing=briefing,
            language_model_id=input_data.language_model_id,
            scene_density=input_data.scene_density,
            canvas=DEFAULT_CANVAS,
            style_preset=style_preset.name,
        )
        video.storyboard = storyboard
        video.status = "storyboard_ready"
        await video.save()

        assets, usage = await generate_scene_assets(
            storyboard=storyboard,
            output_dir=output_dir,
            image_model_id=input_data.image_model_id,
        )
        storyboard_path = output_dir / "storyboard.json"
        storyboard_path.write_text(
            json.dumps(storyboard, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        video.assets = assets
        video.storyboard = storyboard
        video.usage = usage
        video.status = "assets_ready"
        await video.save()

        video_file = render_video_from_storyboard(
            episode=episode,
            storyboard=storyboard,
            output_dir=output_dir,
        )
        video.video_file = video_file
        video.status = "completed"
        video.error_message = None
        await video.save()

        return EpisodeVideoGenerationOutput(
            success=True,
            video_id=str(video.id),
            video_file_path=video_file,
            storyboard_path=str(storyboard_path),
            processing_time=time.time() - start_time,
        )

    except Exception as e:
        logger.error(f"Episode video generation failed: {e}")
        logger.exception(e)
        if video:
            video.status = "failed"
            video.error_message = str(e)
            await video.save()
        return EpisodeVideoGenerationOutput(
            success=False,
            video_id=str(video.id) if video else None,
            video_file_path=None,
            storyboard_path=None,
            processing_time=time.time() - start_time,
            error_message=str(e),
        )
