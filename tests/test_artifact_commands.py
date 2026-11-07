"""Tests for the ``generate_artifact`` command (commands/artifact_commands.py).

The pipeline, the Mermaid engine and pandoc are all stubbed: these tests lock
the COMMAND's own contract - it loads the notebook, writes the rendered files
under the artifacts root, creates the readable note, and reports a path
RELATIVE to that root on the artifact row.
"""

from pathlib import Path

import pytest

import commands.artifact_commands as artifact_commands
import open_notebook.artifacts.paths as artifact_paths

SAMPLE_MARKDOWN = "## Overview\n\nGrounded text [source:1]\n"


class _FakeSource:
    def __init__(self, source_id: str, title: str, url: str = "") -> None:
        self.id = source_id
        self.title = title
        self.asset = {"url": url}


class _FakeNotebook:
    name = "My Notebook"

    async def get_sources(self):
        return [
            _FakeSource("source:1", "Alpha", "https://example.com/alpha"),
            _FakeSource("source:2", "Beta", "https://example.com/beta"),
        ]


class _FakeNotebookModel:
    @classmethod
    async def get(cls, _notebook_id):
        return _FakeNotebook()


class _FakeArtifact:
    def __init__(self, **kwargs):
        self.id = "generated_artifact:1"
        self.title = kwargs.get("title", "My Notebook - Report")
        self.notebook = "notebook:1"
        self.output_path = None
        self.note_id = None
        self.sections = 0
        self.kind = "report"
        self.formats = []
        self.language = "en"
        self.saved = 0

    async def save(self) -> None:
        self.saved += 1


class _FakeArtifactModel:
    instance = _FakeArtifact()

    @classmethod
    async def get(cls, _artifact_id):
        return cls.instance


class _FakeNote:
    created: list["_FakeNote"] = []

    def __init__(self, **kwargs):
        self.id = "note:1"
        self.title = kwargs.get("title")
        self.content = kwargs.get("content")
        self.note_type = kwargs.get("note_type")
        self.notebook = None

    async def save(self) -> None:
        _FakeNote.created.append(self)

    async def add_to_notebook(self, notebook_id: str):
        self.notebook = notebook_id
        return None


def _patch(monkeypatch, tmp_path, *, markdown=SAMPLE_MARKDOWN, formats=None):
    _FakeNote.created = []
    _FakeArtifactModel.instance = _FakeArtifact()
    rendered: dict[str, object] = {}

    async def fake_build_document(
        complete,
        search,
        sources,
        title,
        kind,
        cfg,
        composition=None,
        sections=None,
    ):
        rendered["composition"] = composition
        report = {
            "mode": "retrieval",
            "references": [
                {
                    "number": 1,
                    "source_id": "source:1",
                    "title": "Alpha",
                    "url": "https://example.com/alpha",
                },
                {
                    "number": 2,
                    "source_id": "source:2",
                    "title": "Beta",
                    "url": "https://example.com/beta",
                },
            ],
            "cited_numbers": [1],
            "sections": [
                {
                    "title": "Overview",
                    "thesis": "t",
                    "queries": ["q"],
                    "chunks": [
                        {"source_id": "source:1", "chars": 10, "similarity": 0.5}
                    ],
                }
            ],
            "sections_written": 1,
            "unknown_citations": [],
            "chars": len(markdown),
        }
        return markdown, report

    def fake_render_artifact(
        markdown_text, out_dir, base_name, formats, reference_doc=None
    ):
        outputs = {}
        for fmt in formats:
            target = Path(out_dir) / f"{base_name}.{fmt}"
            target.write_text(markdown_text, encoding="utf-8")
            outputs[fmt] = str(target)
        rendered["outputs"] = outputs
        return outputs

    def fake_search(notebook_id):
        async def search(query, limit, min_score):
            return []

        return search

    monkeypatch.setattr(artifact_commands, "Notebook", _FakeNotebookModel)
    monkeypatch.setattr(artifact_commands, "GeneratedArtifact", _FakeArtifactModel)
    monkeypatch.setattr(artifact_commands, "Note", _FakeNote)
    monkeypatch.setattr(artifact_commands, "build_document", fake_build_document)
    monkeypatch.setattr(artifact_commands, "make_notebook_search", fake_search)
    monkeypatch.setattr(artifact_commands, "render_artifact", fake_render_artifact)
    monkeypatch.setattr(artifact_commands, "ARTIFACTS_FOLDER", str(tmp_path))
    monkeypatch.setattr(artifact_paths, "ARTIFACTS_FOLDER", str(tmp_path))
    return rendered


def _input(**overrides):
    base = {
        "artifact_id": "generated_artifact:1",
        "notebook_id": "notebook:1",
        "kind": "report",
        "formats": ["md", "docx"],
        "language": "en",
        "title": "My Notebook - Report",
        "sections": 5,
    }
    base.update(overrides)
    return artifact_commands.ArtifactGenerationInput(**base)


class TestGenerateArtifactCommand:
    @pytest.mark.asyncio
    async def test_writes_relative_path_note_and_record(self, monkeypatch, tmp_path):
        _patch(monkeypatch, tmp_path)

        result = await artifact_commands.generate_artifact_command(_input())

        assert result.success is True
        assert result.output_path is not None
        assert not Path(result.output_path).is_absolute()
        assert (tmp_path / result.output_path).is_file()
        assert result.note_id == "note:1"
        assert result.sections == 1

        artifact = _FakeArtifactModel.instance
        assert artifact.output_path == result.output_path
        assert artifact.note_id == "note:1"
        assert artifact.formats == ["md", "docx"]
        assert artifact.saved == 1

        assert len(_FakeNote.created) == 1
        note = _FakeNote.created[0]
        assert note.note_type == "ai"
        assert "Grounded text" in (note.content or "")
        # The reference list is written by the command, numbered and linked.
        assert "## References" in (note.content or "")
        assert "1. [Alpha](https://example.com/alpha)" in (note.content or "")
        # Only the cited source is listed.
        assert "Beta" not in (note.content or "")
        assert note.notebook == "notebook:1"

    @pytest.mark.asyncio
    async def test_an_illustrated_report_is_written_with_diagrams(
        self, monkeypatch, tmp_path
    ):
        rendered = _patch(monkeypatch, tmp_path)

        await artifact_commands.generate_artifact_command(
            _input(kind="report", variant="illustrated")
        )

        composition = rendered["composition"]
        assert composition.variant == "illustrated"
        assert composition.allow_diagrams is True

    @pytest.mark.asyncio
    async def test_a_plain_report_is_written_without_diagrams(
        self, monkeypatch, tmp_path
    ):
        rendered = _patch(monkeypatch, tmp_path)

        await artifact_commands.generate_artifact_command(_input(kind="report"))

        composition = rendered["composition"]
        assert composition.variant is None
        assert composition.allow_diagrams is False

    @pytest.mark.asyncio
    async def test_a_variant_of_the_other_kind_fails_the_job(
        self, monkeypatch, tmp_path
    ):
        _patch(monkeypatch, tmp_path)

        with pytest.raises(ValueError):
            await artifact_commands.generate_artifact_command(
                _input(kind="report", variant="presenter")
            )

    @pytest.mark.asyncio
    async def test_unsupported_formats_fall_back_to_default(
        self, monkeypatch, tmp_path
    ):
        _patch(monkeypatch, tmp_path)

        result = await artifact_commands.generate_artifact_command(
            _input(formats=["bogus"])
        )

        assert _FakeArtifactModel.instance.formats == ["md", "docx"]
        assert result.output_path is not None

    @pytest.mark.asyncio
    async def test_empty_document_fails_loudly(self, monkeypatch, tmp_path):
        _patch(monkeypatch, tmp_path, markdown="")

        with pytest.raises(RuntimeError, match="no content"):
            await artifact_commands.generate_artifact_command(_input())

        assert _FakeArtifactModel.instance.output_path is None
        assert _FakeNote.created == []

    @pytest.mark.asyncio
    async def test_no_rendered_output_fails_loudly(self, monkeypatch, tmp_path):
        _patch(monkeypatch, tmp_path)
        monkeypatch.setattr(artifact_commands, "render_artifact", lambda *a, **k: {})

        with pytest.raises(RuntimeError, match="no output file"):
            await artifact_commands.generate_artifact_command(_input())
