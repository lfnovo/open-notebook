"""Regression tests for the app's podcast prompt templates (#1238).

Two defects, neither visible without rendering the templates:

1. The templates showed the model a fill-in JSON skeleton
   (`"speaker": "[Actual Speaker Name]"` plus a bare `...`) inside a ```json
   fence, while also instructing it NOT to use fences. Gemini returned the
   skeleton verbatim - `{"transcript": [{"speaker": "...", "dialogue": "..."}]}`
   - which failed podcast-creator's speaker-name validation and aborted the
   episode mid-run, discarding the segments already generated.

2. These templates shadow podcast-creator's bundled ones (the library resolves
   `Path.cwd()/prompts/podcast/<name>.jinja` before its own package resources)
   and never referenced `{{ language }}`, so `episode_profile.language` looked
   supported and did nothing: Hebrew sources produced an English outline.

Variable names follow podcast_creator.nodes, which renders these templates.
Note the outline template receives `speakers` but NOT `speaker_names`.
"""

import json
import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "podcast"

SPEAKERS = [
    {
        "name": "Marcus Thompson",
        "backstory": "Former consultant",
        "personality": "Strategic",
    },
    {
        "name": "Elena Vasquez",
        "backstory": "Serial entrepreneur",
        "personality": "Pragmatic",
    },
]

# Strings that must never reach the model: each one is copyable as content.
# Angle-bracket descriptions count too - a model that copies
# "<the complete words this speaker says out loud>" into a dialogue value sends
# that straight to the TTS engine, and the templates' own rules ban placeholders.
COPYABLE_SKELETONS = (
    "[Actual Speaker Name]",
    "[Speaker's dialogue based on their personality and expertise]",
    "[Segment Name]",
    "[Description of the segment content]",
    '{"transcript": [...]}',
    '{"segments": [...]}',
    "<the complete words this speaker says out loud, written out in full>",
    "<the real title of this segment>",
    "<the real title of the next segment>",
    "<what is discussed in this segment, including the key points and questions to cover>",
    "<what is discussed in that segment, including the key points and questions to cover>",
)


def render(template_name: str, **data) -> str:
    env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
    return env.get_template(f"{template_name}.jinja").render(**data)


def render_transcript(speakers=None, speaker_names=None, **overrides) -> str:
    speakers = SPEAKERS if speakers is None else speakers
    data = {
        "briefing": "A briefing",
        "context": "Some content",
        "speakers": speakers,
        "speaker_names": [s["name"] for s in speakers]
        if speaker_names is None
        else speaker_names,
        "outline": "An outline",
        "segment": "A segment",
        "turns": 6,
        "is_final": False,
        "transcript": [],
        "format_instructions": "Return JSON",
    }
    data.update(overrides)
    return render("transcript", **data)


def render_outline(**overrides) -> str:
    data = {
        "briefing": "A briefing",
        "context": "Some content",
        "speakers": SPEAKERS,
        "num_segments": 6,
        "format_instructions": "Return JSON",
    }
    data.update(overrides)
    return render("outline", **data)


def example_object(rendered: str, root_key: str) -> dict:
    """Parse the JSON example the prompt shows the model.

    The example is the contract the model imitates, so it has to be valid JSON
    in its own right - a speaker name carrying a quote or a backslash would
    otherwise hand the model a broken example to copy.
    """
    prefix = '{"' + root_key + '":'
    for line in rendered.splitlines():
        if line.startswith(prefix):
            return json.loads(line)
    raise AssertionError(f"no {root_key} example found in the rendered prompt")


class TestExampleIsValidAndComplete:
    """Whatever the model copies from the example must be usable output.

    The example only renders when no language is set (see
    TestNoEnglishSampleInANonEnglishRun), which is what these render.
    """

    def test_transcript_example_parses_and_names_the_speakers(self):
        example = example_object(render_transcript(), "transcript")
        assert [entry["speaker"] for entry in example["transcript"]] == [
            "Marcus Thompson",
            "Elena Vasquez",
        ]

    def test_transcript_example_survives_json_special_characters(self):
        r"""A name like Dr. "Alex" Chen\ must be escaped, not interpolated raw."""
        speakers = [
            {"name": 'Dr. "Alex" Chen\\', "backstory": "b", "personality": "p"},
            {"name": "Jamie\tRodriguez", "backstory": "b", "personality": "p"},
        ]
        example = example_object(render_transcript(speakers=speakers), "transcript")
        assert [entry["speaker"] for entry in example["transcript"]] == [
            'Dr. "Alex" Chen\\',
            "Jamie\tRodriguez",
        ]

    def test_transcript_example_dialogue_is_speakable(self):
        """Dialogue goes straight to TTS, so the example must not contain a
        description of what to write - a copied one would be read aloud. Any
        sentence shape is fine; a placeholder marker or an empty value is not."""
        example = example_object(render_transcript(), "transcript")
        for entry in example["transcript"]:
            dialogue = entry["dialogue"]
            assert dialogue.strip()
            for marker in ("<", ">", "[", "]", "...", "\u2026", "TODO"):
                assert marker not in dialogue

    def test_outline_example_parses_with_valid_sizes(self):
        example = example_object(render_outline(), "segments")
        assert example["segments"]
        for segment in example["segments"]:
            assert segment["size"] in {"short", "medium", "long"}
            assert "<" not in segment["name"]
            assert "<" not in segment["description"]


class TestExampleCannotPassAsACompleteAnswer:
    """The examples are copy-safe by design, which makes them attractive to copy
    wholesale - so they must not read as a finished response. Each is labelled
    an excerpt and restates the count the response actually needs."""

    def test_transcript_example_points_at_the_turn_minimum(self):
        rendered = render_transcript(turns=6)
        assert "two-entry EXCERPT" in rendered
        assert "return at least 6 entries rather than the two shown" in rendered

    def test_solo_excerpt_is_not_called_a_two_entry_one(self):
        """A solo profile renders one entry; calling it a two-entry excerpt
        contradicts the example directly above it."""
        rendered = render_transcript(speakers=[SPEAKERS[0]], turns=3)
        assert "one-entry EXCERPT" in rendered
        assert "two-entry" not in rendered
        assert "rather than the one shown" in rendered

    def test_outline_example_points_at_the_segment_count(self):
        rendered = render_outline(num_segments=6)
        assert "two-entry EXCERPT" in rendered
        assert "return all 6 of them rather than the two shown" in rendered


class TestNoEnglishSampleInANonEnglishRun:
    """The sample values can only be hard-coded English, and a model that
    copies one into a Hebrew episode produces English TTS. For a run with a
    language set, the structure is described in prose instead - the schema
    still reaches the model through format_instructions."""

    @pytest.mark.parametrize(
        "renderer", [render_transcript, render_outline], ids=["transcript", "outline"]
    )
    def test_no_json_sample_when_a_language_is_set(self, renderer):
        rendered = renderer(language="Hebrew")
        assert "EXCERPT" not in rendered
        assert "Let's pick up where we left off" not in rendered
        assert "Setting the scene" not in rendered
        # No JSON object literal is shown at all.
        assert not [
            line for line in rendered.splitlines() if line.startswith('{"')
        ]

    def test_transcript_still_states_the_structure_in_prose(self):
        rendered = render_transcript(turns=6, language="Hebrew")
        assert 'root key "transcript"' in rendered
        assert "at least 6 entries" in rendered
        assert '"speaker" and "dialogue"' in rendered
        assert "{{ speaker_names|join" not in rendered
        assert "Marcus Thompson, Elena Vasquez" in rendered

    def test_outline_still_states_the_structure_in_prose(self):
        rendered = render_outline(num_segments=6, language="Hebrew")
        assert 'root key "segments"' in rendered
        assert "exactly 6 entries" in rendered
        assert '"size" must be exactly one of "short", "medium" or "long"' in rendered


class TestNoCopyableSkeletons:
    """Whatever the model copies from the prompt must be valid output."""

    @pytest.mark.parametrize("skeleton", COPYABLE_SKELETONS)
    def test_transcript_has_no_placeholder_skeleton(self, skeleton):
        assert skeleton not in render_transcript()

    @pytest.mark.parametrize("skeleton", COPYABLE_SKELETONS)
    def test_outline_has_no_placeholder_skeleton(self, skeleton):
        assert skeleton not in render_outline()

    def test_transcript_example_uses_real_speaker_names(self):
        rendered = render_transcript()
        assert '{"transcript": [{"speaker": "Marcus Thompson"' in rendered
        assert '"speaker": "Elena Vasquez"' in rendered

    def test_solo_transcript_example_uses_the_only_speaker(self):
        rendered = render_transcript(speakers=[SPEAKERS[0]])
        assert '{"transcript": [{"speaker": "Marcus Thompson"' in rendered
        assert "Elena Vasquez" not in rendered

    def test_second_speaker_is_guarded_against_a_short_name_list(self):
        """An out-of-range speaker_names[1] would render as an empty string
        under Jinja's default undefined, putting an invalid example in the
        prompt - exactly the failure this template is meant to prevent."""
        rendered = render_transcript(
            speakers=SPEAKERS, speaker_names=["Marcus Thompson"]
        )
        assert '"speaker": ""' not in rendered
        assert rendered.count('"speaker": "Marcus Thompson"') == 2

    def test_transcript_bans_placeholder_content(self):
        rendered = render_transcript()
        assert "Never emit placeholder or elided content" in rendered
        assert "Never shorten or truncate the list" in rendered

    def test_outline_bans_placeholder_content(self):
        rendered = render_outline()
        assert "Never emit placeholder or elided content" in rendered
        assert "never shorten or truncate the list" in rendered

    @pytest.mark.parametrize(
        "renderer", [render_transcript, render_outline], ids=["transcript", "outline"]
    )
    def test_no_code_fence_contradicts_the_no_fence_instruction(self, renderer):
        """The only ``` left may be inside the "no code blocks" rule itself:
        an example wrapped in a fence contradicts that rule and pushes the
        model toward pattern matching over instruction following."""
        rendered = renderer()
        no_fence_rule = "Do NOT wrap the JSON in ```json code blocks"
        assert no_fence_rule in rendered
        assert "```" not in rendered.replace(no_fence_rule, "")


class TestLanguageInstruction:
    """episode_profile.language must actually reach the model (#1238)."""

    def test_transcript_includes_the_language_instruction(self):
        rendered = render_transcript(language="Hebrew")
        assert "IMPORTANT LANGUAGE INSTRUCTION" in rendered
        assert rendered.count("Hebrew") >= 3

    def test_outline_includes_the_language_instruction(self):
        rendered = render_outline(language="Hebrew")
        assert "IMPORTANT LANGUAGE INSTRUCTION" in rendered
        assert "segment names, descriptions" in rendered

    @pytest.mark.parametrize(
        "renderer", [render_transcript, render_outline], ids=["transcript", "outline"]
    )
    def test_no_language_instruction_without_a_language(self, renderer):
        assert "IMPORTANT LANGUAGE INSTRUCTION" not in renderer()
        assert "IMPORTANT LANGUAGE INSTRUCTION" not in renderer(language=None)


class TestNoDriftFromBundledTemplates:
    """The app's copies shadow podcast-creator's, so library prompt work is
    invisible here. The language block was lost exactly this way. Fail when a
    variable the bundled template uses is missing from the app's copy."""

    # Operators and literals a condition can open with: `{% if not language %}`
    # names no variable called "not".
    JINJA_KEYWORDS = frozenset(
        {"not", "and", "or", "is", "in", "if", "else", "true", "false", "none"}
    )

    @classmethod
    def _variables(cls, path: Path) -> set:
        text = path.read_text()
        used = set(re.findall(r"\{\{-?\s*([a-zA-Z_][a-zA-Z0-9_]*)", text))
        used |= set(
            re.findall(r"\{%-?\s*(?:if|elif)\s+([a-zA-Z_][a-zA-Z0-9_]*)", text)
        )
        loop_locals = set(re.findall(r"\{%-?\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)", text))
        return used - loop_locals - cls.JINJA_KEYWORDS

    def test_jinja_keywords_are_not_treated_as_variables(self):
        """`{% if not language %}` names no variable called "not" - counting it
        would fail the drift check the moment one template negates a test the
        other doesn't."""
        assert "not" not in self._variables(PROMPTS_DIR / "transcript.jinja")

    @pytest.mark.parametrize("template", ["transcript", "outline"])
    def test_app_template_uses_every_bundled_variable(self, template):
        import podcast_creator

        bundled = (
            Path(podcast_creator.__file__).parent
            / "resources"
            / "prompts"
            / "podcast"
            / f"{template}.jinja"
        )
        missing = self._variables(bundled) - self._variables(
            PROMPTS_DIR / f"{template}.jinja"
        )
        assert not missing, (
            f"prompts/podcast/{template}.jinja shadows podcast-creator's copy "
            f"but ignores {sorted(missing)}. Either use them or delete the "
            "app template so the library's is used."
        )
