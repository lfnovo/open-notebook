import time
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.config import DATA_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.podcasts.models import (
    EpisodeProfile,
    PodcastEpisode,
    SpeakerProfile,
    _resolve_model_config,
)

try:
    from podcast_creator import configure, create_podcast
except ImportError as e:
    logger.error(f"Failed to import podcast_creator: {e}")
    raise ValueError("podcast_creator library not available")


def full_model_dump(model):
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


class PodcastGenerationInput(CommandInput):
    episode_profile: str
    speaker_profile: str
    episode_name: str
    content: str
    briefing_suffix: Optional[str] = None


class PodcastGenerationOutput(CommandOutput):
    success: bool
    episode_id: Optional[str] = None
    audio_file_path: Optional[str] = None
    transcript: Optional[dict] = None
    outline: Optional[dict] = None
    processing_time: float
    error_message: Optional[str] = None


@command("generate_podcast", app="open_notebook", retry={"max_attempts": 1})
async def generate_podcast_command(
    input_data: PodcastGenerationInput,
) -> PodcastGenerationOutput:
    """
    Real podcast generation using podcast-creator library with Episode Profiles
    """
    start_time = time.time()

    try:
        logger.info(
            f"Starting podcast generation for episode: {input_data.episode_name}"
        )
        logger.info(f"Using episode profile: {input_data.episode_profile}")

        # 1. Load Episode and Speaker profiles from SurrealDB
        episode_profile = await EpisodeProfile.get_by_name(input_data.episode_profile)
        if not episode_profile:
            raise ValueError(
                f"Episode profile '{input_data.episode_profile}' not found"
            )

        speaker_profile = await SpeakerProfile.get_by_name(
            episode_profile.speaker_config
        )
        if not speaker_profile:
            raise ValueError(
                f"Speaker profile '{episode_profile.speaker_config}' not found"
            )

        logger.info(f"Loaded episode profile: {episode_profile.name}")
        logger.info(f"Loaded speaker profile: {speaker_profile.name}")

        # 2. Validate that model registry fields are populated
        if not episode_profile.outline_llm:
            raise ValueError(
                f"Episode profile '{episode_profile.name}' has no outline model configured. "
                "Please update the profile to select an outline model."
            )
        if not episode_profile.transcript_llm:
            raise ValueError(
                f"Episode profile '{episode_profile.name}' has no transcript model configured. "
                "Please update the profile to select a transcript model."
            )
        if not speaker_profile.voice_model:
            raise ValueError(
                f"Speaker profile '{speaker_profile.name}' has no voice model configured. "
                "Please update the profile to select a voice model."
            )

        # 3. Resolve model configs with credentials
        outline_provider, outline_model_name, outline_config = (
            await episode_profile.resolve_outline_config()
        )
        transcript_provider, transcript_model_name, transcript_config = (
            await episode_profile.resolve_transcript_config()
        )
        tts_provider, tts_model_name, tts_config = (
            await speaker_profile.resolve_tts_config()
        )

        logger.info(
            f"Resolved models - outline: {outline_provider}/{outline_model_name}, "
            f"transcript: {transcript_provider}/{transcript_model_name}, "
            f"tts: {tts_provider}/{tts_model_name}"
        )

        # 4. Load all profiles and configure podcast-creator
        episode_profiles = await repo_query("SELECT * FROM episode_profile")
        speaker_profiles = await repo_query("SELECT * FROM speaker_profile")

        # Transform the surrealdb array into a dictionary for podcast-creator
        episode_profiles_dict = {
            profile["name"]: profile for profile in episode_profiles
        }
        speaker_profiles_dict = {
            profile["name"]: profile for profile in speaker_profiles
        }

        # 5. Inject resolved model configs into profile dicts
        # Resolve ALL episode profiles (podcast-creator validates all)
        for ep_name, ep_dict in episode_profiles_dict.items():
            if ep_dict.get("outline_llm"):
                try:
                    prov, model, conf = await _resolve_model_config(
                        str(ep_dict["outline_llm"])
                    )
                    ep_dict["outline_provider"] = prov
                    ep_dict["outline_model"] = model
                    ep_dict["outline_config"] = conf
                except Exception as e:
                    logger.warning(
                        f"Failed to resolve outline model for episode profile '{ep_name}': {e}"
                    )
            if ep_dict.get("transcript_llm"):
                try:
                    prov, model, conf = await _resolve_model_config(
                        str(ep_dict["transcript_llm"])
                    )
                    ep_dict["transcript_provider"] = prov
                    ep_dict["transcript_model"] = model
                    ep_dict["transcript_config"] = conf
                except Exception as e:
                    logger.warning(
                        f"Failed to resolve transcript model for episode profile '{ep_name}': {e}"
                    )

        # Resolve TTS for ALL speaker profiles (podcast-creator validates all)
        for sp_name, sp_dict in speaker_profiles_dict.items():
            if sp_dict.get("voice_model"):
                try:
                    prov, model, conf = await _resolve_model_config(
                        str(sp_dict["voice_model"])
                    )
                    sp_dict["tts_provider"] = prov
                    sp_dict["tts_model"] = model
                    sp_dict["tts_config"] = conf
                except Exception as e:
                    logger.warning(
                        f"Failed to resolve TTS for speaker profile '{sp_name}': {e}"
                    )

            # Per-speaker TTS overrides
            for speaker in sp_dict.get("speakers", []):
                if speaker.get("voice_model"):
                    try:
                        prov, model, conf = await _resolve_model_config(
                            str(speaker["voice_model"])
                        )
                        speaker["tts_provider"] = prov
                        speaker["tts_model"] = model
                        speaker["tts_config"] = conf
                    except Exception as e:
                        logger.warning(
                            f"Failed to resolve per-speaker TTS for '{speaker.get('name')}': {e}"
                        )

        # 6. Generate briefing
        briefing = episode_profile.default_briefing
        if input_data.briefing_suffix:
            briefing += f"\n\nAdditional instructions: {input_data.briefing_suffix}"

        # Create the record for the episode and associate with the ongoing command
        episode = PodcastEpisode(
            name=input_data.episode_name,
            episode_profile=full_model_dump(episode_profile.model_dump()),
            speaker_profile=full_model_dump(speaker_profile.model_dump()),
            command=ensure_record_id(input_data.execution_context.command_id)
            if input_data.execution_context
            else None,
            briefing=briefing,
            content=input_data.content,
            audio_file=None,
            transcript=None,
            outline=None,
        )
        await episode.save()

        configure("speakers_config", {"profiles": speaker_profiles_dict})
        configure("episode_config", {"profiles": episode_profiles_dict})

        logger.info("Configured podcast-creator with episode and speaker profiles")

        logger.info(f"Generated briefing (length: {len(briefing)} chars)")

        # 7. Create output directory
        output_dir = Path(f"{DATA_FOLDER}/podcasts/episodes/{input_data.episode_name}")
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created output directory: {output_dir}")

        # 8. Generate podcast using podcast-creator
        logger.info("Starting podcast generation with podcast-creator...")

        result = await create_podcast(
            content=input_data.content,
            briefing=briefing,
            episode_name=input_data.episode_name,
            output_dir=str(output_dir),
            speaker_config=speaker_profile.name,
            episode_profile=episode_profile.name,
        )

        episode.audio_file = (
            str(result.get("final_output_file_path")) if result else None
        )
        episode.transcript = {
            "transcript": full_model_dump(result["transcript"]) if result else None
        }
        episode.outline = full_model_dump(result["outline"]) if result else None
        await episode.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated podcast episode: {episode.id} in {processing_time:.2f}s"
        )

        return PodcastGenerationOutput(
            success=True,
            episode_id=str(episode.id),
            audio_file_path=str(result.get("final_output_file_path"))
            if result
            else None,
            transcript={"transcript": full_model_dump(result["transcript"])}
            if result.get("transcript")
            else None,
            outline=full_model_dump(result["outline"])
            if result.get("outline")
            else None,
            processing_time=processing_time,
        )

    except ValueError:
        raise

    except Exception as e:
        logger.error(f"Podcast generation failed: {e}")
        logger.exception(e)

        error_msg = str(e)
        if "Invalid json output" in error_msg or "Expecting value" in error_msg:
            error_msg += (
                "\n\nNOTE: This error commonly occurs with GPT-5 models that use extended thinking. "
                "The model may be putting all output inside <think> tags, leaving nothing to parse. "
                "Try using gpt-4o, gpt-4o-mini, or gpt-4-turbo instead in your episode profile."
            )

        raise RuntimeError(error_msg) from e
