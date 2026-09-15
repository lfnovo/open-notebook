"""Podcast TTS voice compatibility preflight tests (#1238)."""

from unittest.mock import AsyncMock, patch

import pytest

from commands.podcast_commands import (
    PodcastGenerationInput,
    generate_podcast_command,
)
from open_notebook.exceptions import NotFoundError
from open_notebook.podcasts.models import (
    _GOOGLE_GEMINI_TTS_VOICES,
    EpisodeProfile,
    PodcastEpisode,
    SpeakerProfile,
)

GEMINI_TTS = ("google", "gemini-3.1-flash-tts-preview", {"api_key": "unused"})


def make_speaker_profile(
    voice_id: str,
    *,
    voice_model: str | None = None,
) -> SpeakerProfile:
    """Build a minimal speaker profile for validation tests."""
    speaker = {
        "name": "Casey",
        "voice_id": voice_id,
        "backstory": "A careful host",
        "personality": "Curious",
    }
    if voice_model:
        speaker["voice_model"] = voice_model
    return SpeakerProfile(
        name="Test Speakers",
        voice_model="model:default-tts",
        speakers=[speaker],
    )


class TestGeminiVoiceValidation:
    @pytest.mark.parametrize(
        "model_name",
        [
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts",
        ],
    )
    def test_static_catalogue_matches_locked_esperanto(self, model_name: str) -> None:
        from esperanto import AIFactory

        model = AIFactory.create_text_to_speech(
            "google", model_name, config={"api_key": "unused"}
        )
        catalogue = model.available_voices or {}
        voice_ids = {str(voice_id).casefold() for voice_id in catalogue}

        assert voice_ids == _GOOGLE_GEMINI_TTS_VOICES

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model_name",
        [
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts",
        ],
    )
    async def test_scoped_gemini_models_accept_voice_case_insensitively(
        self, model_name: str
    ) -> None:
        profile = make_speaker_profile("Kore")

        await profile.validate_tts_voices(
            ("google", model_name, {"api_key": "unused"})
        )

    @pytest.mark.asyncio
    async def test_rejects_incompatible_default_voice(self) -> None:
        profile = make_speaker_profile("echo")

        with pytest.raises(ValueError) as exc_info:
            await profile.validate_tts_voices(GEMINI_TTS)

        message = str(exc_info.value)
        assert "Casey" in message
        assert "echo" in message
        assert "google/gemini-3.1-flash-tts-preview" in message

    @pytest.mark.asyncio
    async def test_uses_per_speaker_model_override(self) -> None:
        profile = make_speaker_profile("echo", voice_model="model:override-tts")

        with patch(
            "open_notebook.podcasts.models._resolve_model_config",
            new=AsyncMock(return_value=GEMINI_TTS),
        ):
            with pytest.raises(ValueError, match="echo"):
                await profile.validate_tts_voices(
                    ("openai", "gpt-4o-mini-tts", {"api_key": "unused"})
                )

    @pytest.mark.asyncio
    async def test_stale_override_uses_non_gemini_default(self) -> None:
        """A missing optional override must not block another provider."""
        profile = make_speaker_profile("echo", voice_model="model:stale")

        with patch(
            "open_notebook.ai.models.Model.get",
            new=AsyncMock(side_effect=NotFoundError("model:stale not found")),
        ):
            await profile.validate_tts_voices(
                ("openai", "gpt-4o-mini-tts", {"api_key": "unused"})
            )

    @pytest.mark.asyncio
    async def test_stale_override_validates_gemini_default(self) -> None:
        """A missing override must still validate the effective default."""
        profile = make_speaker_profile("echo", voice_model="model:stale")

        with patch(
            "open_notebook.ai.models.Model.get",
            new=AsyncMock(side_effect=NotFoundError("model:stale not found")),
        ):
            with pytest.raises(ValueError, match="echo"):
                await profile.validate_tts_voices(GEMINI_TTS)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,model_name",
        [
            ("openai", "gpt-4o-mini-tts"),
            ("google", "future-gemini-tts"),
        ],
    )
    async def test_unknown_catalogue_remains_permissive(
        self, provider: str, model_name: str
    ) -> None:
        profile = make_speaker_profile("provider-specific-voice")

        await profile.validate_tts_voices((provider, model_name, {"api_key": "unused"}))


@pytest.mark.asyncio
async def test_incompatible_voice_stops_before_all_downstream_work(tmp_path) -> None:
    """An invalid Gemini voice must stop before persistence and generation."""
    episode_profile = EpisodeProfile(
        name="Test Episode",
        speaker_config="speaker_profile:test",
        outline_llm="model:outline",
        transcript_llm="model:transcript",
        default_briefing="Discuss the source",
    )
    speaker_profile = make_speaker_profile("echo")
    input_data = PodcastGenerationInput(
        episode_profile="Test Episode",
        speaker_profile="Test Speakers",
        episode_name="Rejected Episode",
        content="Source text",
    )
    repo_query = AsyncMock()
    save = AsyncMock()
    create_podcast = AsyncMock()

    async def resolve_model(model_id: str, max_tokens: int | None = None):
        models = {
            "model:outline": ("openai", "outline", {}),
            "model:transcript": ("openai", "transcript", {}),
            "model:default-tts": GEMINI_TTS,
        }
        return models[model_id]

    with (
        patch.object(
            EpisodeProfile,
            "get_by_name",
            new=AsyncMock(return_value=episode_profile),
        ),
        patch.object(
            SpeakerProfile,
            "resolve",
            new=AsyncMock(return_value=speaker_profile),
        ),
        patch(
            "open_notebook.podcasts.models._resolve_model_config",
            new=resolve_model,
        ),
        patch("commands.podcast_commands.repo_query", new=repo_query),
        patch.object(PodcastEpisode, "save", new=save),
        patch(
            "commands.podcast_commands.build_episode_output_dir",
            new=lambda: ("episode", tmp_path / "episode"),
        ),
        patch("commands.podcast_commands.create_podcast", new=create_podcast),
    ):
        with pytest.raises(ValueError, match="echo"):
            await generate_podcast_command(input_data)

    repo_query.assert_not_awaited()
    save.assert_not_awaited()
    assert list(tmp_path.iterdir()) == []
    create_podcast.assert_not_awaited()
