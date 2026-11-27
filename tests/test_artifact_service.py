"""Tests for ArtifactService.submit_generation_job (api/artifact_service.py).

Locks the ordering the API contract depends on: the artifact row exists (and
is saved) BEFORE the job is submitted, and the job's command id is stored back
on the row so the status endpoint can find it.
"""

from typing import Any

import pytest

import api.artifact_service as service_module
from api.artifact_service import ArtifactService
from open_notebook.exceptions import NotFoundError


class _FakeNotebook:
    name = "Research Notebook"


class _FakeNotebookModel:
    missing = False

    @classmethod
    async def get(cls, _notebook_id):
        if cls.missing:
            raise NotFoundError("notebook not found")
        return _FakeNotebook()


class _FakeArtifact:
    def __init__(self, **kwargs):
        self.id = "generated_artifact:1"
        self.notebook = kwargs.get("notebook")
        self.title = kwargs.get("title")
        self.kind = kwargs.get("kind")
        self.formats = kwargs.get("formats")
        self.language = kwargs.get("language")
        self.sections = kwargs.get("sections")
        self.variant = kwargs.get("variant")
        self.output_path = None
        self.note_id = None
        self.command: Any = None
        self.saved = 0

    async def save(self) -> None:
        self.saved += 1


created: list[_FakeArtifact] = []
submitted: list[tuple] = []


def _patch(monkeypatch):
    created.clear()
    submitted.clear()
    _FakeNotebookModel.missing = False

    def fake_factory(**kwargs):
        artifact = _FakeArtifact(**kwargs)
        created.append(artifact)
        return artifact

    def fake_submit_command(app, name, args):
        submitted.append((app, name, args))
        return "command:1"

    monkeypatch.setattr(service_module, "Notebook", _FakeNotebookModel)
    monkeypatch.setattr(service_module, "GeneratedArtifact", fake_factory)
    monkeypatch.setattr(service_module, "submit_command", fake_submit_command)


class TestSubmitGenerationJob:
    @pytest.mark.asyncio
    async def test_creates_row_then_submits_and_links_command(self, monkeypatch):
        _patch(monkeypatch)

        result = await ArtifactService.submit_generation_job(
            notebook_id="notebook:1", kind="deck", formats=["pptx"]
        )

        assert result == {
            "command_id": "command:1",
            "artifact_id": "generated_artifact:1",
        }
        artifact = created[0]
        assert artifact.saved == 2
        assert artifact.command is not None
        assert artifact.command.table_name == "command"
        assert artifact.kind == "deck"
        assert artifact.formats == ["pptx"]

        app, name, args = submitted[0]
        assert (app, name) == ("open_notebook", "generate_artifact")
        assert args["artifact_id"] == "generated_artifact:1"
        assert args["notebook_id"] == "notebook:1"
        assert args["kind"] == "deck"
        assert args["formats"] == ["pptx"]

    @pytest.mark.asyncio
    async def test_the_variant_is_stored_and_submitted(self, monkeypatch):
        _patch(monkeypatch)

        await ArtifactService.submit_generation_job(
            notebook_id="notebook:1", kind="report", variant="illustrated"
        )

        assert created[0].variant == "illustrated"
        assert submitted[0][2]["variant"] == "illustrated"

    @pytest.mark.asyncio
    async def test_a_variant_of_the_other_kind_is_rejected(self, monkeypatch):
        _patch(monkeypatch)

        with pytest.raises(ValueError):
            await ArtifactService.submit_generation_job(
                notebook_id="notebook:1", kind="report", variant="presenter"
            )

        assert created == []
        assert submitted == []

    @pytest.mark.asyncio
    async def test_unknown_formats_fall_back_to_defaults(self, monkeypatch):
        _patch(monkeypatch)

        await ArtifactService.submit_generation_job(
            notebook_id="notebook:1", formats=["bogus"]
        )

        assert created[0].formats == ["md", "docx"]

    @pytest.mark.asyncio
    async def test_default_title_uses_notebook_and_kind(self, monkeypatch):
        _patch(monkeypatch)

        await ArtifactService.submit_generation_job(
            notebook_id="notebook:1", kind="deck", title="   "
        )

        assert created[0].title == "Research Notebook - Slides"

    @pytest.mark.asyncio
    async def test_missing_notebook_propagates_not_found(self, monkeypatch):
        _patch(monkeypatch)
        _FakeNotebookModel.missing = True

        with pytest.raises(NotFoundError):
            await ArtifactService.submit_generation_job(notebook_id="notebook:missing")

        assert created == []
        assert submitted == []
