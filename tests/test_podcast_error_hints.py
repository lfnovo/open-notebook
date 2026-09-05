"""Hints attached to podcast generation failures (#1238).

The GPT-5 extended-thinking hint used to be the only one, keyed on
`Invalid json output` / `Expecting value`. The two most common real failures
therefore got either nothing (`Invalid speaker name`) or advice about the wrong
provider - a truncated Gemini response was told to switch to gpt-4o.
"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.exceptions import OutputParserException

from commands.podcast_commands import (
    PodcastGenerationInput,
    explain_generation_failure,
    generate_podcast_command,
)


class TestExplainGenerationFailure:
    def test_placeholder_speaker_name_is_explained(self):
        hint = explain_generation_failure(
            "Failed to parse ValidatedTranscript from completion "
            '{"transcript": [{"speaker": "...", "dialogue": "..."}]}. Got: '
            "1 validation error for ValidatedTranscript transcript.0.speaker "
            "Value error, Invalid speaker name '...'. Must be one of: "
            "Marcus Thompson, Elena Vasquez"
        )
        assert hint is not None
        assert "speaker" in hint
        assert "gpt-4o" not in hint

    def test_generic_not_found_names_both_candidates(self):
        """Google returns this for any missing resource, so the hint must not
        send someone to the voice settings when the real fault is a model id
        on the outline or transcript call."""
        hint = explain_generation_failure(
            "Google API error: Requested entity was not found."
        )
        assert hint is not None
        assert "voice_id" in hint
        assert "model id" in hint

    def test_unsupported_voice_name_points_at_the_speaker_profile(self):
        """This message names the voice, so the hint can be specific."""
        hint = explain_generation_failure(
            "Google API error: Voice name echo is not supported. Allowed voice "
            "names are: achernar, achird, algenib"
        )
        assert hint is not None
        assert "voice_id" in hint
        assert "Speaker Profiles" in hint

    @pytest.mark.parametrize(
        "message",
        [
            "Invalid json output: {'transcript': [{'speaker'",
            "Expecting value: line 1 column 1 (char 0)",
        ],
    )
    def test_unparseable_output_mentions_truncation_and_thinking(self, message):
        hint = explain_generation_failure(message)
        assert hint is not None
        assert "max_tokens" in hint
        assert "<think>" in hint

    def test_unrecognised_failure_gets_no_hint(self):
        assert explain_generation_failure("Connection reset by peer") is None


class TestHintsReachTheUser:
    """The mapper is only useful if the failure it describes passes through it.

    `except ValueError: raise` guards the command layer's permanent-failure
    contract, and LangChain's OutputParserException plus json.JSONDecodeError
    are both ValueError subclasses - so every parser failure, which is exactly
    what these hints are for, used to skip the mapper entirely.
    """

    @staticmethod
    def make_input():
        return PodcastGenerationInput(
            episode_profile="Test Episode Profile",
            episode_name="Test Episode",
            content="Some content",
        )

    @pytest.mark.asyncio
    async def test_parser_failure_keeps_its_type_and_gains_the_hint(self):
        parse_error = OutputParserException(
            "Failed to parse ValidatedTranscript from completion "
            '{"transcript": [{"speaker": "...", "dialogue": "..."}]}. Got: '
            "Value error, Invalid speaker name '...'."
        )
        assert isinstance(parse_error, ValueError)

        with patch(
            "commands.podcast_commands.EpisodeProfile.get_by_name",
            AsyncMock(side_effect=parse_error),
        ):
            with pytest.raises(ValueError) as exc_info:
                await generate_podcast_command(self.make_input())

        message = str(exc_info.value)
        assert "Invalid speaker name" in message
        assert "NOTE:" in message
        assert "Speaker names must match the profile exactly" in message
        # Still a ValueError, so the command layer keeps treating it as
        # permanent rather than retrying a failure that will repeat.
        assert not isinstance(exc_info.value, RuntimeError)

    @pytest.mark.asyncio
    async def test_unrecognised_value_error_is_re_raised_untouched(self):
        with patch(
            "commands.podcast_commands.EpisodeProfile.get_by_name",
            AsyncMock(side_effect=ValueError("Episode profile 'x' not found")),
        ):
            with pytest.raises(ValueError) as exc_info:
                await generate_podcast_command(self.make_input())

        assert str(exc_info.value) == "Episode profile 'x' not found"
        assert "NOTE:" not in str(exc_info.value)
