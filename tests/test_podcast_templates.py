"""Our prompts/podcast templates shadow podcast-creator's bundled ones; they
must keep rendering with the variables podcast-creator 0.13 passes (#1435)."""

from types import SimpleNamespace

import pytest

SPEAKERS = [
    SimpleNamespace(name="Ana", backstory="host", personality="curious"),
    SimpleNamespace(name="Bruno", backstory="expert", personality="calm"),
]


@pytest.fixture(autouse=True)
def _repo_root(monkeypatch):
    # podcast-creator resolves templates from ./prompts first.
    from pathlib import Path

    monkeypatch.chdir(Path(__file__).resolve().parent.parent)


def test_outline_template_renders():
    from podcast_creator.core import get_outline_prompter

    text = get_outline_prompter().render(
        {
            "briefing": "Explain RAG",
            "num_segments": 3,
            "context": "RAG combines retrieval and generation.",
            "speakers": SPEAKERS,
            "language": None,
        }
    )
    assert "Explain RAG" in text
    assert "segments" in text
    # Ours, not the bundled template: only ours has the <think> output guidance.
    assert "<think>" in text


@pytest.mark.parametrize("speakers", [SPEAKERS, SPEAKERS[:1]])
def test_transcript_template_renders(speakers):
    from podcast_creator.core import get_transcript_prompter

    segment = SimpleNamespace(name="Intro", description="What RAG is", size="short")
    text = get_transcript_prompter().render(
        {
            "briefing": "Explain RAG",
            "outline": SimpleNamespace(segments=[segment]),
            "context": "RAG combines retrieval and generation.",
            "segment": segment,
            "is_final": True,
            "turns": 3,
            "speakers": speakers,
            "speaker_names": [s.name for s in speakers],
            "transcript": [],
            "language": None,
        }
    )
    assert "Intro" in text
    for s in speakers:
        assert s.name in text
    # Ours, not the bundled template: only ours handles solo episodes.
    assert ("SOLO podcast" in text) == (len(speakers) == 1)
