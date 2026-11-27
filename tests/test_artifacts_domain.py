"""Unit tests for the GeneratedArtifact domain model.

No database is touched: the tests cover the schema contract the model owns
(table name, record-link normalization, validation and save payload).
"""

import pytest
from pydantic import ValidationError
from surrealdb import RecordID

from open_notebook.domain.artifact import GeneratedArtifact


def make_artifact(**overrides):
    """Build a valid artifact with the given field overrides."""
    fields = {
        "notebook": "notebook:nb1",
        "title": "My report",
        "kind": "report",
        "formats": ["md", "pptx"],
        "language": "en",
        "sections": 3,
    }
    fields.update(overrides)
    return GeneratedArtifact(**fields)


class TestSchema:
    def test_table_name_avoids_the_note_edge_table(self):
        assert GeneratedArtifact.table_name == "generated_artifact"
        assert GeneratedArtifact.table_name != "artifact"

    def test_defaults_are_safe_for_a_fresh_record(self):
        artifact = make_artifact()
        assert artifact.id is None
        assert artifact.output_path is None
        assert artifact.note_id is None
        assert artifact.command is None

    def test_optional_links_are_nullable_columns(self):
        assert {
            "output_path",
            "note_id",
            "command",
        } <= GeneratedArtifact.nullable_fields


class TestValidation:
    def test_kind_accepts_report_and_deck(self):
        assert make_artifact(kind="report").kind == "report"
        assert make_artifact(kind="deck").kind == "deck"

    def test_unknown_kind_is_rejected(self):
        with pytest.raises(ValidationError):
            make_artifact(kind="quiz")

    def test_empty_title_is_rejected(self):
        with pytest.raises(ValidationError):
            make_artifact(title="   ")

    def test_empty_format_list_is_rejected(self):
        with pytest.raises(ValidationError):
            make_artifact(formats=[])

    def test_blank_formats_are_rejected(self):
        with pytest.raises(ValidationError):
            make_artifact(formats=["  "])


class TestRecordLinks:
    def test_string_links_are_normalized_to_record_ids(self):
        artifact = make_artifact(
            note_id="note:n1", command="command:c1", notebook="notebook:nb2"
        )
        assert artifact.notebook == RecordID.parse("notebook:nb2")
        assert artifact.note_id == RecordID.parse("note:n1")
        assert artifact.command == RecordID.parse("command:c1")

    def test_save_payload_casts_every_link(self):
        artifact = make_artifact(note_id="note:n1", command="command:c1")
        data = artifact._prepare_save_data()
        assert isinstance(data["notebook"], RecordID)
        assert isinstance(data["note_id"], RecordID)
        assert isinstance(data["command"], RecordID)

    def test_save_payload_survives_strict_validation(self):
        artifact = make_artifact(note_id="note:n1", command="command:c1")
        artifact.model_validate(artifact.model_dump(), strict=True)

    def test_absent_optional_links_stay_out_of_the_create_payload(self):
        data = make_artifact()._prepare_save_data()
        assert data["output_path"] is None
        assert data["note_id"] is None
        assert data["command"] is None
