"""Tests for reading a user-written script as podcast dialogue."""

import pytest

from open_notebook.podcasts.script import MAX_CLIP_CHARS, parse_script

SPEAKERS = ["Velvet Noir", "Max"]


def test_unlabelled_text_goes_to_first_speaker_one_clip_per_paragraph():
    turns = parse_script("Hello there.\nStill me.\n\nNew paragraph.", SPEAKERS)
    assert turns == [
        {"speaker": "Velvet Noir", "dialogue": "Hello there. Still me."},
        {"speaker": "Velvet Noir", "dialogue": "New paragraph."},
    ]


def test_speaker_labels_switch_voice_case_insensitively():
    script = "velvet noir: Welcome back.\nMAX: Thanks.\nAnd more from Max."
    assert parse_script(script, SPEAKERS) == [
        {"speaker": "Velvet Noir", "dialogue": "Welcome back."},
        {"speaker": "Max", "dialogue": "Thanks. And more from Max."},
    ]


def test_markdown_bold_labels_and_formatting_are_stripped():
    script = (
        "---\ntitle: Ep 1\n---\n"
        "# The Case\n\n"
        "**Max:** This is *really* `odd`, see [the file](http://x.y).\n\n"
        "- first point\n> quoted line\n\n***\n<br>"
    )
    assert parse_script(script, SPEAKERS) == [
        {"speaker": "Velvet Noir", "dialogue": "The Case"},
        {"speaker": "Max", "dialogue": "This is really odd, see the file."},
        {"speaker": "Max", "dialogue": "first point quoted line"},
    ]


def test_unknown_label_is_read_as_text():
    assert parse_script("Note: read this aloud.", SPEAKERS) == [
        {"speaker": "Velvet Noir", "dialogue": "Note: read this aloud."}
    ]


def test_long_paragraph_splits_on_sentence_boundaries():
    sentence = "This sentence is exactly fifty characters long ok. "
    turns = parse_script(sentence * 100, SPEAKERS)
    assert len(turns) > 1
    assert all(len(t["dialogue"]) <= MAX_CLIP_CHARS for t in turns)
    assert all(t["dialogue"].endswith(".") for t in turns)
    joined = " ".join(t["dialogue"] for t in turns)
    assert joined == (sentence * 100).strip()


def test_single_overlong_sentence_is_hard_split():
    turns = parse_script("word " * 1000, SPEAKERS)
    assert all(0 < len(t["dialogue"]) <= MAX_CLIP_CHARS for t in turns)


def test_empty_script_raises():
    with pytest.raises(ValueError):
        parse_script("  \n# \n---\n", SPEAKERS)
