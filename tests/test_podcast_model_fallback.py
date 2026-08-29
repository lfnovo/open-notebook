"""
Tests for podcast generation's outline/transcript large-context fallback
loop (commands/podcast_commands.py::generate_podcast_command).

Podcast generation goes through the external podcast_creator library, which
only accepts raw (provider, model_name) strings - it has no injection point
for the LangChain with_fallbacks() cascade chat/transformations already use
(open_notebook/ai/provision.py). This adds an in-function retry loop: on a
non-ValueError failure of the primary outline/transcript model, retry with
each configured DefaultModels.large_context_fallback_models entry (resolved
through the same _resolve_model_config() helper), in order, before giving
up. A ValueError raised by podcast-creator's own config validation is a
permanent failure by this repo's convention and must never trigger a
fallback attempt - but pydantic.ValidationError (a ValueError subclass
covering a model returning malformed/empty output) is treated as an
ordinary retryable failure instead, since a different model may succeed.

No database is available in tests: profile lookups, model resolution, and
podcast-creator itself are all mocked. Covers:
  (a) no fallback chain configured -> exactly one attempt, unchanged
      behavior/error propagation
  (b) primary fails with a non-ValueError, one fallback configured ->
      fallback succeeds, episode completes using it
  (c) primary fails with a plain ValueError -> raises immediately, fallback
      never attempted even though one is configured
  (d) primary fails with pydantic.ValidationError -> falls back normally,
      like any other transient exception
  (e) primary AND all fallbacks fail -> raises a RuntimeError summarizing
      every attempt
"""

from contextlib import ExitStack
from types import SimpleNamespace
from typing import Dict, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ValidationError

from commands.podcast_commands import (
    MAX_PODCAST_FALLBACK_ATTEMPTS,
    PodcastGenerationInput,
    generate_podcast_command,
)
from open_notebook.podcasts.models import EpisodeProfile, PodcastEpisode, SpeakerProfile

# (provider, model_name, config) canned resolutions, keyed by the model
# record ID that would appear in outline_llm/transcript_llm/voice_model or
# DefaultModels.large_context_fallback_models.
MODEL_RESOLUTIONS: Dict[str, Tuple[str, str, dict]] = {
    "model:outline": ("openrouter", "primary-outline-model", {}),
    "model:transcript": ("openrouter", "primary-transcript-model", {}),
    "model:voice": ("openai", "tts-1", {}),
    "model:fallback-a": ("openrouter", "fallback-model-a", {}),
    "model:fallback-b": ("openrouter", "fallback-model-b", {}),
    "model:fallback-c": ("openrouter", "fallback-model-c", {}),
    "model:fallback-d": ("openrouter", "fallback-model-d", {}),
}


async def fake_resolve_model_config(model_id, max_tokens=None):
    if model_id not in MODEL_RESOLUTIONS:
        raise AssertionError(f"unexpected model_id resolved in test: {model_id}")
    return MODEL_RESOLUTIONS[model_id]


def make_episode_profile(**overrides):
    defaults = dict(
        id="episode_profile:test",
        name="default",
        description=None,
        speaker_config="speaker_profile:test",
        outline_llm="model:outline",
        transcript_llm="model:transcript",
        language=None,
        default_briefing="Test briefing",
        num_segments=5,
        max_tokens=None,
    )
    defaults.update(overrides)
    return EpisodeProfile(**defaults)


def make_speaker_profile(**overrides):
    defaults = dict(
        id="speaker_profile:test",
        name="default",
        description=None,
        voice_model="model:voice",
        speakers=[
            {
                "name": "Host",
                "voice_id": "voice-1",
                "backstory": "A curious host.",
                "personality": "Warm and inquisitive.",
            }
        ],
    )
    defaults.update(overrides)
    return SpeakerProfile(**defaults)


def make_input():
    return PodcastGenerationInput(
        episode_profile="default",
        episode_name="Test Episode",
        content="test content",
    )


def episode_profile_row(**overrides):
    row = dict(
        id="episode_profile:test",
        name="default",
        speaker_config="speaker_profile:test",
        outline_llm="model:outline",
        transcript_llm="model:transcript",
        max_tokens=None,
    )
    row.update(overrides)
    return row


def speaker_profile_row(**overrides):
    row = dict(
        id="speaker_profile:test",
        name="default",
        voice_model="model:voice",
        speakers=[
            {
                "name": "Host",
                "voice_id": "voice-1",
                "backstory": "A curious host.",
                "personality": "Warm and inquisitive.",
            }
        ],
    )
    row.update(overrides)
    return row


def make_repo_query_mock():
    return AsyncMock(side_effect=[[episode_profile_row()], [speaker_profile_row()]])


def make_default_models(fallback_ids):
    return SimpleNamespace(large_context_fallback_models=list(fallback_ids))


def common_patches(stack: ExitStack, create_podcast_mock, fallback_ids=()):
    """Enter every patch covering the DB/library boundaries
    generate_podcast_command touches, so tests only need to vary
    create_podcast's behavior and the configured fallback chain."""
    episode_profile = make_episode_profile()
    speaker_profile = make_speaker_profile()

    stack.enter_context(
        patch.object(
            EpisodeProfile, "get_by_name", new=AsyncMock(return_value=episode_profile)
        )
    )
    stack.enter_context(
        patch.object(
            SpeakerProfile, "resolve", new=AsyncMock(return_value=speaker_profile)
        )
    )
    stack.enter_context(
        patch.object(
            EpisodeProfile,
            "resolve_outline_config",
            new=AsyncMock(return_value=("openrouter", "primary-outline-model", {})),
        )
    )
    stack.enter_context(
        patch.object(
            EpisodeProfile,
            "resolve_transcript_config",
            new=AsyncMock(
                return_value=("openrouter", "primary-transcript-model", {})
            ),
        )
    )
    stack.enter_context(
        patch.object(
            SpeakerProfile,
            "resolve_tts_config",
            new=AsyncMock(return_value=("openai", "tts-1", {})),
        )
    )
    stack.enter_context(
        patch("commands.podcast_commands.repo_query", new=make_repo_query_mock())
    )
    stack.enter_context(
        patch(
            "commands.podcast_commands._resolve_model_config",
            new=AsyncMock(side_effect=fake_resolve_model_config),
        )
    )
    stack.enter_context(
        patch.object(PodcastEpisode, "save", new=AsyncMock(return_value=None))
    )
    stack.enter_context(patch("commands.podcast_commands.configure", new=MagicMock()))
    stack.enter_context(
        patch("commands.podcast_commands.create_podcast", new=create_podcast_mock)
    )
    stack.enter_context(
        patch(
            "commands.podcast_commands.DefaultModels.get_instance",
            new=AsyncMock(return_value=make_default_models(fallback_ids)),
        )
    )


def fake_result():
    return {
        "final_output_file_path": None,
        "transcript": {"segments": []},
        "outline": {"sections": []},
    }


class TestNoFallbackConfigured:
    @pytest.mark.asyncio
    async def test_single_attempt_on_success(self):
        """No fallback chain configured -> exactly one create_podcast call."""
        create_podcast_mock = AsyncMock(return_value=fake_result())
        with ExitStack() as stack:
            common_patches(stack, create_podcast_mock, fallback_ids=[])
            output = await generate_podcast_command(make_input())

        assert output.success is True
        create_podcast_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_single_attempt_failure_propagates_unchanged(self):
        """No fallback configured -> on failure, the ORIGINAL exception
        propagates through generate_podcast_command's own error-enrichment
        wrapper exactly as it did before this feature existed (strict
        no-regression case)."""
        create_podcast_mock = AsyncMock(
            side_effect=RuntimeError("upstream exploded")
        )
        with ExitStack() as stack:
            common_patches(stack, create_podcast_mock, fallback_ids=[])
            with pytest.raises(RuntimeError, match="upstream exploded"):
                await generate_podcast_command(make_input())

        create_podcast_mock.assert_awaited_once()


class TestFallbackOnNonValueError:
    @pytest.mark.asyncio
    async def test_fallback_succeeds_after_primary_fails(self):
        create_podcast_mock = AsyncMock(
            side_effect=[
                RuntimeError(
                    "{'message': 'Upstream error from Nvidia: Service temporarily"
                    " overloaded', 'code': 502}"
                ),
                fake_result(),
            ]
        )
        with ExitStack() as stack:
            common_patches(
                stack, create_podcast_mock, fallback_ids=["model:fallback-a"]
            )
            output = await generate_podcast_command(make_input())

        assert output.success is True
        assert create_podcast_mock.await_count == 2


class _StrictModel(BaseModel):
    """Used only to manufacture a real pydantic.ValidationError below."""

    x: int


def make_validation_error() -> ValidationError:
    try:
        _StrictModel(x="not an int")
    except ValidationError as e:
        return e
    raise AssertionError("expected pydantic to reject this input")


class TestValidationErrorFallsBack:
    """Regression test for a real failure hit live: a fallback model (under
    concurrent-load overload) returned malformed/empty output, and
    podcast-creator's own structured-output parsing raised a
    pydantic.ValidationError. Since ValidationError IS a ValueError
    subclass, it used to be caught by the "permanent failure, never
    fall back" branch and killed the whole job on one flaky response -
    exactly the case the fallback chain exists to route around. It must
    instead take the normal attempt/fallback path, same as any other
    transient exception."""

    @pytest.mark.asyncio
    async def test_validation_error_falls_back_and_succeeds(self):
        create_podcast_mock = AsyncMock(
            side_effect=[make_validation_error(), fake_result()]
        )
        with ExitStack() as stack:
            common_patches(
                stack, create_podcast_mock, fallback_ids=["model:fallback-a"]
            )
            output = await generate_podcast_command(make_input())

        assert output.success is True
        assert create_podcast_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_validation_error_on_last_attempt_summarizes_all(self):
        create_podcast_mock = AsyncMock(
            side_effect=[RuntimeError("primary overloaded"), make_validation_error()]
        )
        with ExitStack() as stack:
            common_patches(
                stack, create_podcast_mock, fallback_ids=["model:fallback-a"]
            )
            with pytest.raises(RuntimeError) as exc_info:
                await generate_podcast_command(make_input())

        assert create_podcast_mock.await_count == 2
        message = str(exc_info.value)
        assert "primary overloaded" in message
        assert "fallback-model-a" in message


class TestValueErrorNeverFallsBack:
    @pytest.mark.asyncio
    async def test_value_error_raises_immediately_no_fallback_attempted(self):
        create_podcast_mock = AsyncMock(
            side_effect=ValueError("permanent: invalid episode configuration")
        )
        with ExitStack() as stack:
            common_patches(
                stack, create_podcast_mock, fallback_ids=["model:fallback-a"]
            )
            with pytest.raises(ValueError, match="permanent: invalid"):
                await generate_podcast_command(make_input())

        create_podcast_mock.assert_awaited_once()


class TestAllAttemptsFail:
    @pytest.mark.asyncio
    async def test_runtime_error_summarizes_every_attempt(self):
        create_podcast_mock = AsyncMock(
            side_effect=[
                RuntimeError("primary overloaded"),
                RuntimeError("fallback also overloaded"),
            ]
        )
        with ExitStack() as stack:
            common_patches(
                stack, create_podcast_mock, fallback_ids=["model:fallback-a"]
            )
            with pytest.raises(RuntimeError) as exc_info:
                await generate_podcast_command(make_input())

        assert create_podcast_mock.await_count == 2
        message = str(exc_info.value)
        assert "primary overloaded" in message
        assert "fallback also overloaded" in message
        assert "primary-outline-model" in message
        assert "fallback-model-a" in message


class TestFallbackAttemptCap:
    @pytest.mark.asyncio
    async def test_extra_fallbacks_beyond_cap_are_skipped(self):
        """4 fallback models configured, cap is 3 -> primary + 3 fallbacks
        = 4 total attempts, the 4th configured fallback is never tried."""
        assert MAX_PODCAST_FALLBACK_ATTEMPTS == 3
        create_podcast_mock = AsyncMock(
            side_effect=RuntimeError("always fails")
        )
        with ExitStack() as stack:
            common_patches(
                stack,
                create_podcast_mock,
                fallback_ids=[
                    "model:fallback-a",
                    "model:fallback-b",
                    "model:fallback-c",
                    "model:fallback-d",
                ],
            )
            with pytest.raises(RuntimeError) as exc_info:
                await generate_podcast_command(make_input())

        # primary + first 3 fallbacks = 4 attempts, never a 5th for fallback-d
        assert create_podcast_mock.await_count == 4
        assert "fallback-model-d" not in str(exc_info.value)
