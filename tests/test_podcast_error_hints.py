"""Hints attached to podcast generation failures (#1238).

The GPT-5 extended-thinking hint used to be the only one, keyed on
`Invalid json output` / `Expecting value`. The two most common real failures
therefore got either nothing (`Invalid speaker name`) or advice about the wrong
provider - a truncated Gemini response was told to switch to gpt-4o.
"""

import pytest

from commands.podcast_commands import explain_generation_failure


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

    def test_google_bad_voice_points_at_the_speaker_profile(self):
        hint = explain_generation_failure(
            "Google API error: Requested entity was not found."
        )
        assert hint is not None
        assert "voice_id" in hint
        assert "Speaker Profiles" in hint

    def test_unsupported_voice_name_points_at_the_speaker_profile(self):
        hint = explain_generation_failure(
            "Google API error: Voice name echo is not supported. Allowed voice "
            "names are: achernar, achird, algenib"
        )
        assert hint is not None
        assert "voice_id" in hint

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
