"""Generated artifact domain model (#203 artifacts tab, stage 1).

One row per generated report or slide deck. The row is the job handle: it
carries the request (notebook, kind, formats, language, sections) and the
result (``output_path``, ``note_id``, ``command``), so the API can poll it the
same way it polls podcast episodes.

The table is ``generated_artifact`` and NOT ``artifact``: ``artifact`` is
already the note -> notebook edge table (see migration 1 and
``Note.add_to_notebook()``), so naming this entity ``artifact`` would write
generated-artifact rows into a relation table and break every note relation.

``output_path`` follows the podcast convention (``podcasts/audio_paths.py``):
the column stores a path RELATIVE to ``ARTIFACTS_FOLDER``, never an absolute or
escaping path, so the value stays valid when ``DATA_FOLDER`` moves and the
download endpoint can reject traversal with a simple containment check.
"""

from typing import ClassVar, Literal, Optional, Union

from pydantic import ConfigDict, Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.base import ObjectModel


class GeneratedArtifact(ObjectModel):
    """A generated report or slide deck tied to a notebook.

    Attributes:
        notebook: Notebook record link the artifact was generated from.
        title: Human title used for the document and the file names.
        kind: ``report`` (prose document) or ``deck`` (slide presentation).
        variant: Sub-variant of the kind: ``document``/``illustrated`` for a
            report, ``presenter``/``detailed`` for a deck. ``None`` means the
            kind's default was used.
        formats: Requested output formats, a subset of ``md``, ``html``,
            ``docx``, ``pptx`` (``md`` is always written as the pandoc input).
        language: Language the document body is written in.
        sections: Number of sections the planner produced.
        output_path: Path to the primary output file, relative to
            ``ARTIFACTS_FOLDER``. ``None`` while the job is still running.
        note_id: Note created in the notebook with the readable report.
        command: Link to the surreal-commands job running the generation.
    """

    table_name: ClassVar[str] = "generated_artifact"
    nullable_fields: ClassVar[set[str]] = {"output_path", "note_id", "command"}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    notebook: Union[str, RecordID] = Field(..., description="Notebook record link")
    title: str = Field(..., description="Document title")
    kind: Literal["report", "deck"] = Field(..., description="Artifact kind")
    variant: Optional[str] = Field(
        default=None,
        description="Kind sub-variant: document/illustrated, presenter/detailed",
    )
    formats: list[str] = Field(
        default_factory=list, description="Requested output formats"
    )
    language: str = Field(default="en", description="Document language")
    sections: int = Field(default=0, description="Number of planned sections")
    output_path: Optional[str] = Field(
        default=None,
        description="Primary output file, relative to ARTIFACTS_FOLDER",
    )
    note_id: Optional[Union[str, RecordID]] = Field(
        default=None, description="Note record created in the notebook"
    )
    command: Optional[Union[str, RecordID]] = Field(
        default=None, description="Link to the surreal-commands job"
    )

    @field_validator("notebook", "note_id", "command", mode="before")
    @classmethod
    def parse_record_links(cls, value):
        """Normalize record links so Pydantic accepts the plain string form."""
        if isinstance(value, str) and value:
            return ensure_record_id(value)
        return value

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        """Reject an empty title: it makes the output file names unusable."""
        if not value.strip():
            raise ValueError("Artifact title cannot be empty")
        return value

    @field_validator("formats")
    @classmethod
    def formats_must_not_be_empty(cls, value: list[str]) -> list[str]:
        """Reject an empty format list: there would be nothing to download."""
        if not [fmt for fmt in value if fmt.strip()]:
            raise ValueError("Artifact formats cannot be empty")
        return value

    def _prepare_save_data(self) -> dict:
        """Cast every record link field to RecordID before the write."""
        data = super()._prepare_save_data()
        for field_name in ("notebook", "note_id", "command"):
            if data.get(field_name) is not None:
                data[field_name] = ensure_record_id(data[field_name])
        return data
