import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import ValidationError
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.ai.models import DefaultModels
from open_notebook.config import PODCASTS_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.podcasts.audio_paths import to_relative_audio_path
from open_notebook.podcasts.models import (
    EpisodeProfile,
    PodcastEpisode,
    SpeakerProfile,
    _resolve_model_config,
)
from open_notebook.utils.model_utils import full_model_dump

try:
    from podcast_creator import configure, create_podcast
except ImportError as e:
    logger.error(f"Failed to import podcast_creator: {e}")
    raise ValueError("podcast_creator library not available")

# Cap on how many configured large-context fallback models podcast
# generation will try (on top of the primary model) before giving up. Book-
# length content makes each attempt slow and potentially costly (a big
# model call against 700k+ chars), so an unbounded walk through a long
# user-configured fallback chain risks a single episode running for hours.
# 3 gives a meaningful safety net (primary + 3 fallbacks = 4 total tries)
# without that risk; any extra configured fallbacks beyond this are logged
# and skipped rather than silently ignored.
MAX_PODCAST_FALLBACK_ATTEMPTS = 3


def build_episode_output_dir(podcasts_folder: str = PODCASTS_FOLDER) -> tuple[str, Path]:
    """Build a filesystem-safe output directory path for a podcast episode.

    Uses a UUID as the directory name so the path is safe regardless of
    what the user typed as episode name (spaces, special chars, etc.).

    Builds under PODCASTS_FOLDER — the same root to_relative_audio_path()
    validates against at write time (#1030) — so the two can't drift apart.

    Returns:
        A tuple of (episode_dir_name, output_dir_path).
    """
    episode_dir_name = str(uuid.uuid4())
    output_dir = Path(podcasts_folder) / "episodes" / episode_dir_name
    return episode_dir_name, output_dir


class PodcastGenerationInput(CommandInput):
    episode_profile: str
    # Speaker profile record ID or name (the API boundary resolves the
    # user-facing name to a record ID before submitting; both are accepted
    # here for robustness).
    speaker_profile: Optional[str] = None
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

        # Honor the explicitly requested speaker profile when provided,
        # falling back to the episode profile's configured speaker
        # (a speaker_profile record ID since migration 20, None when the
        # referenced profile no longer exists).
        speaker_ref = input_data.speaker_profile or episode_profile.speaker_config
        if not speaker_ref:
            raise ValueError(
                f"Episode profile '{episode_profile.name}' has no speaker "
                "profile configured. Please update the profile to select a "
                "speaker profile."
            )
        speaker_profile = await SpeakerProfile.resolve(speaker_ref)
        if not speaker_profile:
            if input_data.speaker_profile:
                raise ValueError(f"Speaker profile '{speaker_ref}' not found")
            raise ValueError(
                f"Episode profile '{episode_profile.name}' references a "
                "speaker profile that no longer exists. Please update the "
                "profile to select a speaker profile."
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

        # Map speaker_profile record ID -> name so podcast-creator keeps
        # receiving speaker names (its EpisodeProfile.speaker_config is a
        # required non-empty name string, cross-referenced against the
        # speakers config keyed by name).
        speaker_name_by_id = {
            str(profile["id"]): profile["name"] for profile in speaker_profiles
        }

        # 5. Inject resolved model configs into profile dicts
        # Resolve ALL episode profiles (podcast-creator validates all).
        # Remove profiles that fail resolution to prevent validation errors.
        for ep_name in list(episode_profiles_dict.keys()):
            ep_dict = episode_profiles_dict[ep_name]

            # Since migration 20, speaker_config stores a record ID (and is
            # None when the referenced speaker profile no longer exists).
            # Rewrite it back to the speaker name for podcast-creator; drop
            # profiles whose reference doesn't resolve so a single orphaned
            # profile can't fail validation for the whole config. The profile
            # being generated always resolves: its speaker was validated above.
            speaker_ref = ep_dict.get("speaker_config")
            speaker_name = (
                speaker_name_by_id.get(str(speaker_ref)) if speaker_ref else None
            )
            if not speaker_name and ep_name == episode_profile.name:
                speaker_name = speaker_profile.name
            if not speaker_name:
                logger.warning(
                    f"Episode profile '{ep_name}' references a speaker profile "
                    f"that no longer exists ({speaker_ref!r}), removing from "
                    "config to prevent validation errors"
                )
                del episode_profiles_dict[ep_name]
                continue
            ep_dict["speaker_config"] = speaker_name

            try:
                if ep_dict.get("outline_llm"):
                    prov, model, conf = await _resolve_model_config(
                        str(ep_dict["outline_llm"]),
                        max_tokens=ep_dict.get("max_tokens"),
                    )
                    ep_dict["outline_provider"] = prov
                    ep_dict["outline_model"] = model
                    ep_dict["outline_config"] = conf
                if ep_dict.get("transcript_llm"):
                    prov, model, conf = await _resolve_model_config(
                        str(ep_dict["transcript_llm"]),
                        max_tokens=ep_dict.get("max_tokens"),
                    )
                    ep_dict["transcript_provider"] = prov
                    ep_dict["transcript_model"] = model
                    ep_dict["transcript_config"] = conf
            except Exception as e:
                logger.warning(
                    f"Failed to resolve models for episode profile '{ep_name}', "
                    f"removing from config to prevent validation errors: {e}"
                )
                del episode_profiles_dict[ep_name]

        # Resolve TTS for ALL speaker profiles (podcast-creator validates all).
        # Remove profiles that fail resolution to prevent validation errors.
        for sp_name in list(speaker_profiles_dict.keys()):
            sp_dict = speaker_profiles_dict[sp_name]
            if not sp_dict.get("voice_model"):
                # podcast-creator's SpeakerProfile requires tts_provider/
                # tts_model with no default (unlike EpisodeProfile's
                # outline/transcript fields, which have hardcoded defaults) -
                # an unconfigured voice_model here is not a resolution
                # *failure*, it was simply never set (default seed data), so
                # there's nothing to try/except. Drop it the same way a
                # failed resolution is dropped below, or podcast-creator's
                # own SpeakerConfig validation crashes on this profile even
                # though it's unrelated to the episode being generated.
                logger.warning(
                    f"Speaker profile '{sp_name}' has no voice model "
                    "configured, removing from config to prevent validation "
                    "errors"
                )
                del speaker_profiles_dict[sp_name]
                continue
            try:
                prov, model, conf = await _resolve_model_config(
                    str(sp_dict["voice_model"])
                )
                sp_dict["tts_provider"] = prov
                sp_dict["tts_model"] = model
                sp_dict["tts_config"] = conf
            except Exception as e:
                logger.warning(
                    f"Failed to resolve TTS for speaker profile '{sp_name}', "
                    f"removing from config to prevent validation errors: {e}"
                )
                del speaker_profiles_dict[sp_name]
                continue

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

        # SECURITY NOTE for future work: podcast_creator also supports
        # configure("templates", {...}), which compiles the given string
        # directly as Jinja2 template *source* (Prompter(template_text=...)
        # in podcast_creator/config.py) - the exact SSTI shape already fixed
        # in open_notebook/graphs/transformation.py (GHSA-f35w-wx37-26q7).
        # We don't call it today (confirmed: no code path here sets the
        # "templates" key, so podcast generation always uses the file-based
        # prompts/podcast/*.jinja templates in this repo). If a "custom
        # podcast template" feature is ever added, do NOT wire user/profile
        # text into configure("templates", ...) - render it through a
        # fixed, developer-authored template with the user text passed in
        # as a plain variable instead, matching transformation.py's fix.
        configure("speakers_config", {"profiles": speaker_profiles_dict})

        logger.info("Configured podcast-creator with speaker profiles")

        logger.info(f"Generated briefing (length: {len(briefing)} chars)")

        # 7. Create output directory using UUID for filesystem-safe paths
        episode_dir_name, output_dir = build_episode_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created output directory: {output_dir}")

        # 8. Build the ordered list of model attempts: attempt 0 is the
        # already-resolved primary outline/transcript config (today's only
        # attempt), attempts 1..N re-resolve each configured large-context
        # fallback model (Settings -> Models -> large context fallback
        # chain) through the same _resolve_model_config() helper and use
        # that SAME model for both outline and transcript stages - a
        # book-sized-context failure (hang, overload, deprecation) affects
        # both stages identically, so there's no benefit in mixing per-role
        # fallback models here. With no fallback chain configured (the
        # common case), this list has exactly one entry and behavior below
        # is unchanged from before this feature existed.
        # NOTE: outline_provider/transcript_provider (and their model/config
        # siblings) are only present on primary_ep_dict when the profile row
        # actually had outline_llm/transcript_llm set (step 5's `if
        # ep_dict.get("outline_llm"):` guard) - a row missing that field
        # (e.g. seeded before the model registry existed) intentionally
        # leaves these keys unset so podcast-creator falls back to its own
        # hardcoded default model. `.get()` (not `[...]`) preserves that:
        # the "primary" attempt just carries (None, None, None) for that
        # role, and the per-attempt loop below skips overwriting it.
        primary_ep_dict = episode_profiles_dict[episode_profile.name]
        attempts: List[Dict[str, Any]] = [
            {
                "label": (
                    f"primary ({primary_ep_dict.get('outline_provider')}/"
                    f"{primary_ep_dict.get('outline_model')})"
                ),
                "outline": (
                    primary_ep_dict.get("outline_provider"),
                    primary_ep_dict.get("outline_model"),
                    primary_ep_dict.get("outline_config"),
                ),
                "transcript": (
                    primary_ep_dict.get("transcript_provider"),
                    primary_ep_dict.get("transcript_model"),
                    primary_ep_dict.get("transcript_config"),
                ),
            }
        ]

        try:
            default_models = await DefaultModels.get_instance()
            fallback_model_ids = list(default_models.large_context_fallback_models or [])
        except Exception as e:
            logger.warning(
                f"Failed to load large-context fallback model chain for podcast "
                f"generation, proceeding with the primary model only: {e}"
            )
            fallback_model_ids = []

        if len(fallback_model_ids) > MAX_PODCAST_FALLBACK_ATTEMPTS:
            logger.info(
                f"{len(fallback_model_ids)} large-context fallback models "
                f"configured; capping podcast generation at the first "
                f"{MAX_PODCAST_FALLBACK_ATTEMPTS} to bound total runtime/cost "
                "against book-length content."
            )
            fallback_model_ids = fallback_model_ids[:MAX_PODCAST_FALLBACK_ATTEMPTS]

        for fallback_model_id in fallback_model_ids:
            try:
                fb_provider, fb_model_name, fb_config = await _resolve_model_config(
                    fallback_model_id, max_tokens=episode_profile.max_tokens
                )
            except Exception as e:
                logger.warning(
                    f"Failed to resolve fallback model '{fallback_model_id}' for "
                    f"podcast generation, skipping it: {e}"
                )
                continue
            attempts.append(
                {
                    "label": f"fallback ({fb_provider}/{fb_model_name})",
                    "outline": (fb_provider, fb_model_name, fb_config),
                    "transcript": (fb_provider, fb_model_name, fb_config),
                }
            )

        # 9. Generate podcast using podcast-creator, walking the attempts
        # list in order. A ValueError raised directly by podcast-creator's
        # own config validation (bad speaker/episode profile, missing
        # briefing, etc. - see its config.py/episodes.py/speakers.py) is a
        # permanent failure no fallback model can fix, and propagates
        # immediately. pydantic.ValidationError is technically also a
        # ValueError subclass but means something different here: the
        # outline/transcript model returned malformed or empty output
        # (observed live - "Failed to parse ValidatedTranscript from
        # completion null" - when a fallback model choked mid-overload) -
        # that's exactly what the fallback chain exists to route around, so
        # it takes the normal attempt/fallback path below instead of
        # short-circuiting the whole job on one flaky response.
        # Any other exception also moves on to the next attempt; when every
        # attempt is exhausted the last error is raised (unchanged, single-
        # attempt propagation when no fallback is configured; a summarizing
        # RuntimeError when there were fallbacks to report on).
        logger.info("Starting podcast generation with podcast-creator...")

        result = None
        attempt_errors: List[str] = []
        for i, attempt in enumerate(attempts):
            o_provider, o_model, o_config = attempt["outline"]
            t_provider, t_model, t_config = attempt["transcript"]
            ep_dict = episode_profiles_dict[episode_profile.name]
            # Only overwrite a role's provider/model/config when this attempt
            # actually resolved one - an unresolved primary role (see NOTE
            # above) is left untouched so podcast-creator's own default
            # keeps applying to it, exactly as before this feature existed.
            if o_provider is not None:
                ep_dict["outline_provider"] = o_provider
                ep_dict["outline_model"] = o_model
                ep_dict["outline_config"] = o_config
            if t_provider is not None:
                ep_dict["transcript_provider"] = t_provider
                ep_dict["transcript_model"] = t_model
                ep_dict["transcript_config"] = t_config
            configure("episode_config", {"profiles": episode_profiles_dict})

            logger.info(
                f"Podcast generation attempt {i + 1}/{len(attempts)}: "
                f"{attempt['label']}"
            )
            try:
                result = await create_podcast(
                    content=input_data.content,
                    briefing=briefing,
                    episode_name=episode_dir_name,
                    output_dir=str(output_dir),
                    speaker_config=speaker_profile.name,
                    episode_profile=episode_profile.name,
                )
                logger.info(
                    f"Podcast generation succeeded on attempt {i + 1}/{len(attempts)} "
                    f"using {attempt['label']}"
                )
                break
            except ValueError as e:
                if not isinstance(e, ValidationError):
                    # Permanent failure - never retried with a fallback model.
                    raise
                logger.warning(
                    f"Podcast generation attempt {i + 1}/{len(attempts)} failed "
                    f"using {attempt['label']} (model returned invalid output): {e}"
                )
                attempt_errors.append(f"{attempt['label']}: {e}")
                if i == len(attempts) - 1:
                    if len(attempts) == 1:
                        raise
                    raise RuntimeError(
                        f"Podcast generation failed after {len(attempts)} "
                        "attempts: " + " | ".join(attempt_errors)
                    ) from e
            except Exception as e:
                logger.warning(
                    f"Podcast generation attempt {i + 1}/{len(attempts)} failed "
                    f"using {attempt['label']}: {e}"
                )
                attempt_errors.append(f"{attempt['label']}: {e}")
                if i == len(attempts) - 1:
                    if len(attempts) == 1:
                        # No fallback chain configured: preserve today's
                        # exact error propagation, unchanged (strict
                        # no-regression case - see class docstring/AGENTS.md).
                        raise
                    raise RuntimeError(
                        f"Podcast generation failed after {len(attempts)} "
                        "attempts: " + " | ".join(attempt_errors)
                    ) from e

        # Every failure path above (ValueError re-raise, single-attempt
        # re-raise, or the summarizing RuntimeError on the last attempt)
        # exits the function before reaching here, so `result` is always
        # set by this point - this only narrows the type for mypy (`result`
        # is seeded to None above so the loop can be typed) without
        # changing runtime behavior.
        assert result is not None

        # podcast-creator reports audio-combination failures IN-BAND: on
        # ffmpeg/clip errors combine_audio_files() returns an "ERROR: ..."
        # string in final_output_file_path instead of a path. Detect it
        # before path conversion so the real error surfaces (below, after
        # the transcript/outline are persisted) instead of a misleading
        # "outside the podcasts folder" ValueError.
        raw_audio_path = result.get("final_output_file_path") if result else None
        audio_error: Optional[str] = None
        if raw_audio_path is not None and str(raw_audio_path).startswith("ERROR:"):
            audio_error = str(raw_audio_path)
            raw_audio_path = None

        # Store the audio path RELATIVE to PODCASTS_FOLDER (#1030). The
        # validation inside to_relative_audio_path guarantees the DB never
        # holds an absolute or root-escaping value; a violation raises
        # ValueError, which marks the job permanently failed (no retry).
        audio_file_rel = (
            to_relative_audio_path(raw_audio_path) if raw_audio_path else None
        )
        episode.audio_file = audio_file_rel
        episode.transcript = {
            "transcript": full_model_dump(result["transcript"]) if result else None
        }
        episode.outline = full_model_dump(result["outline"]) if result else None
        await episode.save()

        if audio_error:
            # Transcript/outline are saved above; fail the job with the real
            # audio-combination error instead of reporting a silent success
            # for an episode with no playable audio.
            raise RuntimeError(f"Podcast audio generation failed: {audio_error}")

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated podcast episode: {episode.id} in {processing_time:.2f}s"
        )

        return PodcastGenerationOutput(
            success=True,
            episode_id=str(episode.id),
            audio_file_path=audio_file_rel,
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
