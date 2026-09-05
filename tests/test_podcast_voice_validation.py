"""Voice-id pre-flight for podcast speaker profiles (#1238).

Migration 7 seeds speaker profiles with OpenAI voice names (`nova`, `alloy`,
`echo`, `shimmer`, `ash`) while the live TTS model is whatever `voice_model`
points at. With a Gemini voice model every audio clip fails - after the whole
transcript has been generated and paid for - with `Google API error: Requested
entity was not found.`, which reads like a missing model rather than a bad
voice.

`SpeakerProfile.validate_voices()` runs before generation instead, but must not
be trigger-happy: esperanto's hard-coded catalogues go stale (its OpenAI list
predates `ash`, which the API accepts), so only a voice another provider's
catalogue claims is treated as an error.

No network and no credentials: the providers exercised here return literal
dicts from `available_voices`.
"""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.podcasts.models import SpeakerProfile
from open_notebook.podcasts.voices import (
    STATIC_CATALOGUE_PROVIDERS,
    VoiceCatalogueCache,
    config_fingerprint,
    find_voice_mismatch,
    format_voice_list,
    get_known_voice_ids,
)

GEMINI_TTS = ("google", "gemini-3.1-flash-tts-preview", {"api_key": "unused"})


def make_profile(speakers, name="business_panel"):
    return SpeakerProfile(
        name=name,
        voice_model="model:tts",
        speakers=[
            {"backstory": "b", "personality": "p", **speaker} for speaker in speakers
        ],
    )


class TestVoiceCatalogue:
    @pytest.mark.asyncio
    async def test_gemini_catalogue_is_available_offline_and_lowercased(self):
        voices = await get_known_voice_ids(*GEMINI_TTS)
        assert voices is not None
        # Gemini documents its voices capitalised (Kore); esperanto lists them
        # lower-cased. Both must match, since the API accepts either.
        assert "kore" in voices
        assert "echo" not in voices

    @pytest.mark.asyncio
    async def test_unknown_provider_skips_validation(self):
        assert await get_known_voice_ids("not-a-provider", "x", {}) is None

    @pytest.mark.asyncio
    async def test_openai_voice_is_attributed_to_openai(self):
        """Azure OpenAI TTS ships the same voice names, so both are named -
        either way the voice demonstrably isn't Gemini's."""
        mismatch = await find_voice_mismatch(*GEMINI_TTS, "echo")
        assert mismatch is not None
        assert mismatch.confident
        assert "openai" in mismatch.other_providers

    @pytest.mark.asyncio
    async def test_unattributable_voice_is_not_confident(self):
        """`ash` is a real OpenAI voice missing from esperanto's list; nothing
        can be concluded from its absence, so the run must not be blocked."""
        mismatch = await find_voice_mismatch(*GEMINI_TTS, "ash")
        assert mismatch is not None
        assert not mismatch.confident

    @pytest.mark.asyncio
    async def test_valid_voice_reports_no_mismatch(self):
        assert await find_voice_mismatch(*GEMINI_TTS, "Kore") is None

    @pytest.mark.asyncio
    async def test_cache_keeps_endpoints_apart(self):
        """Two Model records can share a provider and model name while pointing
        at different accounts or endpoints (a second API key, another
        `base_url`/`endpoint_tts`). An ElevenLabs voice library is per-account,
        so sharing one catalogue across them validates a speaker against voices
        it cannot use."""

        async def per_account(provider, model_name=None, config=None):
            return {"voice-" + (config or {}).get("api_key", "none")}

        cache = VoiceCatalogueCache()
        with patch("open_notebook.podcasts.voices.get_known_voice_ids", per_account):
            account_a = await cache.get(
                "elevenlabs", "eleven_turbo_v2", {"api_key": "acct-a"}
            )
            account_b = await cache.get(
                "elevenlabs", "eleven_turbo_v2", {"api_key": "acct-b"}
            )
            repeat_a = await cache.get(
                "elevenlabs", "eleven_turbo_v2", {"api_key": "acct-a"}
            )

        assert account_a == {"voice-acct-a"}
        assert account_b == {"voice-acct-b"}
        # Same config still hits the memo rather than the provider.
        assert repeat_a is account_a

    @pytest.mark.asyncio
    @pytest.mark.parametrize("provider", STATIC_CATALOGUE_PROVIDERS)
    async def test_every_attribution_provider_resolves_offline(self, provider):
        """A provider that can't be constructed from placeholder credentials
        contributes nothing and spends the retry budget on every pass - which
        is why Vertex is not on this list."""
        from open_notebook.podcasts.voices import catalogue_only_config

        voices = await get_known_voice_ids(
            provider, config=catalogue_only_config(provider)
        )
        assert voices

    @pytest.mark.asyncio
    async def test_a_deepgram_voice_is_attributed_to_deepgram(self):
        """Deepgram's catalogue is a literal dict too, so its voices can be
        placed as confidently as OpenAI's."""
        mismatch = await find_voice_mismatch(*GEMINI_TTS, "aura-2-thalia-en")
        assert mismatch is not None
        assert mismatch.confident
        assert "deepgram" in mismatch.other_providers

    def test_fingerprint_is_stable_across_nested_key_order(self):
        """Sorting only the top level would give one config two digests
        depending on how a nested mapping happened to be ordered."""
        one = {"api_key": "k", "options": {"a": 1, "b": {"x": 1, "y": 2}}}
        two = {"options": {"b": {"y": 2, "x": 1}, "a": 1}, "api_key": "k"}
        assert config_fingerprint(one) == config_fingerprint(two)

    def test_fingerprint_separates_different_nested_values(self):
        one = {"api_key": "k", "options": {"region": "eu"}}
        two = {"api_key": "k", "options": {"region": "us"}}
        assert config_fingerprint(one) != config_fingerprint(two)

    def test_fingerprint_handles_unserializable_values(self):
        assert config_fingerprint({"session": object()})

    def test_voice_list_is_capped(self):
        formatted = format_voice_list({f"v{i:02d}" for i in range(30)}, limit=3)
        assert formatted == "v00, v01, v02, … (30 total)"


class TestValidateVoices:
    @pytest.mark.asyncio
    async def test_seeded_openai_voice_on_gemini_fails_immediately(self):
        profile = make_profile(
            [
                {"name": "Marcus Thompson", "voice_id": "echo"},
                {"name": "Elena Vasquez", "voice_id": "shimmer"},
            ]
        )
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with pytest.raises(ValueError) as exc_info:
                await profile.validate_voices()

        message = str(exc_info.value)
        # Names the speaker, the voice, the model and the valid alternatives -
        # everything "Requested entity was not found" left the operator to guess.
        assert "Marcus Thompson" in message
        assert "'echo'" in message
        assert "google/gemini-3.1-flash-tts-preview" in message
        assert "kore" in message
        assert "Speaker Profiles" in message

    @pytest.mark.asyncio
    async def test_gemini_voices_pass_case_insensitively(self):
        profile = make_profile([{"name": "Speaker", "voice_id": "Kore"}])
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            await profile.validate_voices()

    @pytest.mark.asyncio
    async def test_unattributable_voice_warns_instead_of_raising(self):
        """`ash` is a real OpenAI voice absent from esperanto's list, so the run
        proceeds - but it has to say so, otherwise the eventual provider error
        arrives with nothing in the log pointing at the voice. (loguru doesn't
        propagate to caplog, hence patching the module's logger.)"""
        profile = make_profile([{"name": "Johny Bing", "voice_id": "ash"}])
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with patch("open_notebook.podcasts.models.logger") as mock_logger:
                await profile.validate_voices()

        mock_logger.warning.assert_called_once()
        warning = mock_logger.warning.call_args.args[0]
        assert "Johny Bing" in warning
        assert "'ash'" in warning
        assert "google/gemini-3.1-flash-tts-preview" in warning

    @pytest.mark.asyncio
    @pytest.mark.parametrize("blank", ["", "   ", None])
    async def test_blank_voice_fails_immediately(self, blank):
        """A blank voice matches no catalogue and belongs to no provider, so it
        would otherwise fall into the "can't attribute it" branch and only warn -
        then fail during audio generation like the bug this pre-flight fixes."""
        profile = make_profile([{"name": "Speaker", "voice_id": blank}])
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with pytest.raises(ValueError, match="has no voice"):
                await profile.validate_voices()

    @pytest.mark.asyncio
    async def test_padded_voice_is_rejected_rather_than_trimmed(self):
        """podcast-creator sends the stored value to the provider, so trimming
        for the check would clear a voice the TTS call still fails on."""
        profile = make_profile([{"name": "Speaker", "voice_id": " kore "}])
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with pytest.raises(ValueError) as exc_info:
                await profile.validate_voices()

        message = str(exc_info.value)
        assert "whitespace" in message
        assert "' kore '" in message

    @pytest.mark.asyncio
    async def test_catalogue_is_fetched_once_per_profile(self):
        """Catalogues can't change between speakers of one profile, and an
        HTTP-backed provider charges a request (up to 10s) per lookup."""
        profile = make_profile(
            [
                {"name": "A", "voice_id": "voice-a"},
                {"name": "B", "voice_id": "voice-b"},
                {"name": "C", "voice_id": "voice-c"},
            ]
        )
        catalogue = AsyncMock(return_value={"voice-a", "voice-b", "voice-c"})
        with patch.object(
            SpeakerProfile,
            "resolve_tts_config",
            AsyncMock(return_value=("elevenlabs", "eleven_turbo_v2", {})),
        ):
            with patch(
                "open_notebook.podcasts.voices.get_known_voice_ids", catalogue
            ):
                await profile.validate_voices()

        assert catalogue.await_count == 1

    @pytest.mark.asyncio
    async def test_speakers_on_different_accounts_are_checked_separately(self):
        """Two speakers overriding voice_model to the same provider and model
        name but different credentials must each be checked against their own
        account's voices - not the first one's."""
        profile = make_profile(
            [
                {
                    "name": "A",
                    "voice_id": "voice-acct-a",
                    "voice_model": "model:account_a",
                },
                {
                    "name": "B",
                    "voice_id": "voice-acct-b",
                    "voice_model": "model:account_b",
                },
            ]
        )
        configs = {
            "model:account_a": ("elevenlabs", "eleven_turbo_v2", {"api_key": "acct-a"}),
            "model:account_b": ("elevenlabs", "eleven_turbo_v2", {"api_key": "acct-b"}),
        }

        async def per_account(provider, model_name=None, config=None):
            return {"voice-" + (config or {}).get("api_key", "none")}

        with patch(
            "open_notebook.podcasts.models._resolve_model_config",
            AsyncMock(side_effect=lambda model_id: configs[model_id]),
        ):
            with patch(
                "open_notebook.podcasts.voices.get_known_voice_ids", per_account
            ):
                with patch("open_notebook.podcasts.models.logger") as mock_logger:
                    await profile.validate_voices()

        # Both voices are valid for their own account: nothing to warn about.
        mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_off_lookup_failure_does_not_disable_the_rest_of_the_pass(self):
        """A timeout and an unknown provider both surface as None, so caching
        the first failure would let one flaky request switch validation off for
        every later speaker."""
        from open_notebook.podcasts import voices as voices_module

        real_lookup = voices_module.get_known_voice_ids
        attempts = {"n": 0}

        async def flaky(provider, model_name=None, config=None):
            attempts["n"] += 1
            if attempts["n"] == 1:
                return None
            return await real_lookup(provider, model_name, config)

        profile = make_profile(
            [{"name": "A", "voice_id": "echo"}, {"name": "B", "voice_id": "echo"}]
        )
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with patch("open_notebook.podcasts.voices.get_known_voice_ids", flaky):
                with pytest.raises(ValueError) as exc_info:
                    await profile.validate_voices()

        # Speaker A was skipped, but B's lookup succeeded and caught the voice.
        assert "Speaker 'B'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_a_dead_catalogue_is_not_retried_once_per_speaker(self):
        """The retry above must stay bounded: an endpoint that is simply down
        would otherwise cost CATALOGUE_TIMEOUT_SECONDS for every speaker."""
        from open_notebook.podcasts.voices import MAX_CATALOGUE_ATTEMPTS

        profile = make_profile(
            [{"name": name, "voice_id": "voice-x"} for name in "ABCD"]
        )
        catalogue = AsyncMock(return_value=None)
        with patch.object(
            SpeakerProfile,
            "resolve_tts_config",
            AsyncMock(return_value=("elevenlabs", "eleven_turbo_v2", {})),
        ):
            with patch(
                "open_notebook.podcasts.voices.get_known_voice_ids", catalogue
            ):
                await profile.validate_voices()

        assert catalogue.await_count == MAX_CATALOGUE_ATTEMPTS

    @pytest.mark.asyncio
    async def test_attribution_catalogues_are_not_re_enumerated_per_speaker(self):
        """Attributing an unknown voice enumerates the static catalogues; two
        speakers with the same problem must not pay for them twice. A catalogue
        that fails to resolve (Vertex without a project id) is the one thing
        retried, and only up to MAX_CATALOGUE_ATTEMPTS."""
        from collections import Counter

        from open_notebook.podcasts import voices as voices_module
        from open_notebook.podcasts.voices import MAX_CATALOGUE_ATTEMPTS

        real_lookup = voices_module.get_known_voice_ids
        lookups = []

        async def spy(provider, model_name=None, config=None):
            lookups.append((provider, model_name))
            return await real_lookup(provider, model_name, config)

        profile = make_profile(
            [{"name": "A", "voice_id": "ash"}, {"name": "B", "voice_id": "ash"}]
        )
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ):
            with patch("open_notebook.podcasts.voices.get_known_voice_ids", spy):
                await profile.validate_voices()

        counts = Counter(lookups)
        assert counts
        # Catalogues that resolve are fetched exactly once for the whole
        # profile, however many speakers need checking: the resolved model's
        # own, and OpenAI's from the attribution step.
        assert counts[(GEMINI_TTS[0], GEMINI_TTS[1])] == 1
        assert counts[("openai", None)] == 1
        # Every attribution provider resolves offline now, so nothing needs a
        # second attempt; the ceiling still bounds the failing case.
        assert max(counts.values()) == 1
        assert max(counts.values()) <= MAX_CATALOGUE_ATTEMPTS

    @pytest.mark.asyncio
    async def test_unavailable_catalogue_never_blocks_generation(self):
        profile = make_profile([{"name": "Speaker", "voice_id": "whatever"}])
        with patch.object(
            SpeakerProfile,
            "resolve_tts_config",
            AsyncMock(return_value=("elevenlabs", "eleven_turbo_v2", {})),
        ):
            with patch(
                "open_notebook.podcasts.voices.get_known_voice_ids",
                AsyncMock(return_value=None),
            ):
                await profile.validate_voices()

    @pytest.mark.asyncio
    async def test_per_speaker_voice_model_override_is_used(self):
        """A speaker may override the profile's voice model, so the voice has
        to be checked against the override, not the profile default."""
        profile = make_profile(
            [{"name": "Speaker", "voice_id": "echo", "voice_model": "model:openai_tts"}]
        )
        with patch.object(
            SpeakerProfile, "resolve_tts_config", AsyncMock(return_value=GEMINI_TTS)
        ) as profile_config:
            with patch(
                "open_notebook.podcasts.models._resolve_model_config",
                AsyncMock(return_value=("openai", "gpt-4o-mini-tts", {"api_key": "x"})),
            ) as override_config:
                await profile.validate_voices()

        override_config.assert_awaited_once_with("model:openai_tts")
        profile_config.assert_not_awaited()
