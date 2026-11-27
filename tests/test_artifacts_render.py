"""Unit tests for the pandoc rendering step.

``pypandoc.convert_file`` is reached through a single indirection
(``render._pandoc_convert``) which every test monkeypatches, so no pandoc
binary is executed and no file is really converted.
"""

from pathlib import Path

from open_notebook.artifacts import render


def _record_convert(monkeypatch, calls, fail_on=None):
    """Replace the pandoc call site with a recorder writing a stub file."""

    def convert(source, to, outputfile, extra_args):
        calls.append(
            {
                "source": source,
                "to": to,
                "outputfile": outputfile,
                "extra_args": list(extra_args),
            }
        )
        if to == fail_on:
            raise RuntimeError("pandoc is not available")
        Path(outputfile).write_text("rendered", encoding="utf-8")

    monkeypatch.setattr(render, "_pandoc_convert", convert)


class TestHelpers:
    def test_slugify_is_filesystem_safe(self):
        assert render.slugify("My Report: 2026 / v2!") == "my-report-2026-v2"

    def test_slugify_falls_back_when_nothing_is_left(self):
        assert render.slugify("???") == "artifact"

    def test_base_name_combines_slug_and_kind(self):
        assert render.build_base_name("My Report", "deck") == "my-report-deck"

    def test_base_name_without_a_title_uses_the_kind(self):
        assert render.build_base_name("", "report") == "report-report"

    def test_the_reference_deck_ships_with_the_package(self):
        deck = render.reference_deck_path()
        assert deck is not None
        assert deck.name == render.REFERENCE_DECK_NAME
        assert deck.is_file()


class TestRenderArtifact:
    def test_markdown_and_pptx_are_written_with_the_reference_deck(
        self, monkeypatch, tmp_path
    ):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)

        outputs = render.render_artifact("# Doc\n", tmp_path, "doc", ["md", "pptx"])

        assert set(outputs) == {"md", "pptx"}
        assert (tmp_path / "doc.md").read_text(encoding="utf-8") == "# Doc\n"
        assert calls[0]["to"] == "pptx"
        assert calls[0]["source"].endswith("doc.md")
        assert f"--resource-path={tmp_path}" in calls[0]["extra_args"]
        assert (
            f"--reference-doc={render.reference_deck_path()}" in calls[0]["extra_args"]
        )

    def test_html_is_standalone_and_gets_no_pptx_reference(self, monkeypatch, tmp_path):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)

        render.render_artifact("# Doc\n", tmp_path, "doc", ["html"])

        assert calls[0]["to"] == "html"
        assert "--standalone" in calls[0]["extra_args"]
        assert not any(
            arg.startswith("--reference-doc") for arg in calls[0]["extra_args"]
        )

    def test_every_requested_format_is_converted(self, monkeypatch, tmp_path):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)

        outputs = render.render_artifact(
            "# Doc\n", tmp_path, "doc", ["md", "html", "docx", "pptx"]
        )

        assert set(outputs) == {"md", "html", "docx", "pptx"}
        assert [call["to"] for call in calls] == ["html", "docx", "pptx"]

    def test_markdown_is_a_removed_work_file_when_not_requested(
        self, monkeypatch, tmp_path
    ):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)

        outputs = render.render_artifact("# Doc\n", tmp_path, "doc", ["pptx"])

        assert "md" not in outputs
        assert not (tmp_path / "doc.md").exists()
        assert not (tmp_path / ".doc.source.md").exists()
        assert calls[0]["source"].endswith(".doc.source.md")

    def test_unsupported_format_is_skipped_without_a_pandoc_call(
        self, monkeypatch, tmp_path
    ):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)

        outputs = render.render_artifact("# Doc\n", tmp_path, "doc", ["md", "pdf"])

        assert set(outputs) == {"md"}
        assert calls == []

    def test_a_failing_format_does_not_abort_the_others(self, monkeypatch, tmp_path):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls, fail_on="pptx")

        outputs = render.render_artifact(
            "# Doc\n", tmp_path, "doc", ["md", "docx", "pptx"]
        )

        assert set(outputs) == {"md", "docx"}
        assert [call["to"] for call in calls] == ["docx", "pptx"]

    def test_an_explicit_reference_applies_only_to_its_own_format(
        self, monkeypatch, tmp_path
    ):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)
        deck = tmp_path / "custom.docx"

        render.render_artifact(
            "# Doc\n", tmp_path, "doc", ["docx", "pptx"], reference_doc=deck
        )

        docx_extra = calls[0]["extra_args"]
        pptx_extra = calls[1]["extra_args"]
        assert f"--reference-doc={deck}" in docx_extra
        assert not any(arg.startswith("--reference-doc") for arg in pptx_extra)

    def test_output_directory_is_created(self, monkeypatch, tmp_path):
        calls: list[dict] = []
        _record_convert(monkeypatch, calls)
        nested = tmp_path / "run" / "nested"

        render.render_artifact("# Doc\n", nested, "doc", ["md"])

        assert (nested / "doc.md").is_file()
