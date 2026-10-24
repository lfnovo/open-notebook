"""Service layer for generated artifacts (#203 artifacts tab).

Thin, synchronous-facing wrapper around the ``generate_artifact`` command and
the ``GeneratedArtifact`` rows, mirroring ``api/podcast_service.py``: the
router stays declarative, the job submission and the DB/file handling live
here.

The row is created HERE, before the command is submitted, so ``POST
/api/artifacts`` can return an ``artifact_id`` the frontend can poll right
away; the command then fills in ``output_path``, ``note_id`` and ``sections``.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from surreal_commands import get_command_status, submit_command

from open_notebook.artifacts.outline import normalize_kind, normalize_variant
from open_notebook.artifacts.paths import (
    resolve_contained_artifact_path,
    to_relative_artifact_path,
)
from open_notebook.artifacts.render import SUPPORTED_FORMATS
from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.artifact import GeneratedArtifact
from open_notebook.domain.notebook import Notebook

#: Formats requested when the caller asks for none.
DEFAULT_FORMATS = ["md", "docx"]

_KIND_LABELS = {"report": "Report", "deck": "Slides"}


class ArtifactService:
    """Submission, listing and file cleanup for generated artifacts."""

    @staticmethod
    def default_title(notebook_name: str, kind: str) -> str:
        """Build the document title used when the user provides none.

        Args:
            notebook_name: Name of the source notebook.
            kind: Normalized artifact kind.

        Returns:
            ``"<notebook> - <Report|Slides>"``.
        """
        return f"{notebook_name or 'Notebook'} - {_KIND_LABELS.get(kind, 'Report')}"

    @staticmethod
    def _requested_formats(formats: Optional[List[str]]) -> List[str]:
        """Keep only supported formats, defaulting when nothing usable is left.

        Args:
            formats: Formats requested by the user.

        Returns:
            A non-empty list of supported formats.
        """
        chosen = [fmt for fmt in (formats or []) if fmt in SUPPORTED_FORMATS]
        return chosen or list(DEFAULT_FORMATS)

    @staticmethod
    async def submit_generation_job(
        notebook_id: str,
        kind: str = "report",
        formats: Optional[List[str]] = None,
        language: str = "en",
        title: Optional[str] = None,
        instructions: Optional[str] = None,
        sections: int = 10,
        model_id: Optional[str] = None,
        variant: Optional[str] = None,
    ) -> Dict[str, str]:
        """Create the artifact row and submit the generation job.

        Args:
            notebook_id: Notebook to generate from; must exist.
            kind: ``report`` or ``deck`` (``slides`` accepted as an alias).
            formats: Requested output formats.
            language: Language the document body is written in.
            title: Optional explicit title.
            instructions: Optional user brief for the writer.
            sections: Maximum number of sections to plan.
            model_id: Optional explicit Model record id.
            variant: Optional kind sub-variant (``document``/``illustrated``
                for a report, ``presenter``/``detailed`` for a deck).

        Returns:
            ``{"command_id": ..., "artifact_id": ...}``.

        Raises:
            NotFoundError: If the notebook does not exist.
            ValueError: If the command module cannot be imported, or the
                variant does not belong to the requested kind.
        """
        notebook = await Notebook.get(notebook_id)

        norm_kind = normalize_kind(kind)
        requested_variant = (variant or "").strip()
        norm_variant = (
            normalize_variant(norm_kind, requested_variant)
            if requested_variant
            else None
        )
        chosen = ArtifactService._requested_formats(formats)
        doc_title = (title or "").strip() or ArtifactService.default_title(
            notebook.name, norm_kind
        )
        max_sections = max(1, int(sections or 10))

        artifact = GeneratedArtifact(
            notebook=notebook_id,
            title=doc_title,
            kind=norm_kind,
            variant=norm_variant,
            formats=chosen,
            language=language or "en",
            sections=max_sections,
        )
        await artifact.save()
        artifact_id = str(artifact.id)

        # Ensure command modules are imported before submitting: submit_command
        # validates against the local registry.
        try:
            import commands.artifact_commands  # noqa: F401
        except ImportError as import_err:
            logger.error(f"Failed to import artifact commands: {import_err}")
            raise ValueError("Artifact commands not available")

        job_id = submit_command(
            "open_notebook",
            "generate_artifact",
            {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "kind": norm_kind,
                "variant": norm_variant,
                "formats": chosen,
                "language": artifact.language,
                "title": doc_title,
                "instructions": instructions,
                "sections": max_sections,
                "model_id": model_id,
            },
        )
        if not job_id:
            raise ValueError("Failed to get a job id from submit_command")

        artifact.command = ensure_record_id(str(job_id))
        await artifact.save()

        logger.info(
            f"Submitted artifact generation job {job_id} for artifact {artifact_id}"
        )
        return {"command_id": str(job_id), "artifact_id": artifact_id}

    @staticmethod
    async def list_artifacts(
        notebook_id: Optional[str] = None,
    ) -> List[GeneratedArtifact]:
        """List artifacts, newest first, optionally filtered by notebook.

        Args:
            notebook_id: Optional notebook record id to filter on.

        Returns:
            The matching artifacts.
        """
        artifacts = await GeneratedArtifact.get_all(order_by="created desc")
        if not notebook_id:
            return artifacts
        return [
            artifact
            for artifact in artifacts
            if str(artifact.notebook or "") == notebook_id
        ]

    @staticmethod
    async def get_artifact(artifact_id: str) -> GeneratedArtifact:
        """Load one artifact.

        Args:
            artifact_id: Artifact record id.

        Returns:
            The artifact.

        Raises:
            NotFoundError: If the artifact does not exist.
        """
        return await GeneratedArtifact.get(artifact_id)

    @staticmethod
    async def get_job_status(command_id: Optional[str]) -> Dict[str, Any]:
        """Resolve the status of the job behind an artifact.

        Args:
            command_id: ``GeneratedArtifact.command`` value, may be ``None``.

        Returns:
            ``{"status": ..., "error_message": ...}``; ``status`` is
            ``"unknown"`` when the link is missing or the job is unreadable.
        """
        if not command_id:
            return {"status": "unknown", "error_message": None}
        try:
            status = await get_command_status(str(command_id))
        except Exception as exc:
            logger.warning(f"Failed to read artifact job status {command_id}: {exc}")
            return {"status": "unknown", "error_message": None}
        if not status:
            return {"status": "unknown", "error_message": None}
        return {
            "status": status.status,
            "error_message": getattr(status, "error_message", None),
        }

    @staticmethod
    def available_files(artifact: GeneratedArtifact) -> List[str]:
        """List the requested formats that actually exist on disk.

        Args:
            artifact: Artifact row to inspect.

        Returns:
            The available formats, in the order stored on the row.
        """
        primary = resolve_contained_artifact_path(artifact.output_path)
        if primary is None or not primary.exists():
            return []
        base_name = primary.stem
        return [
            fmt
            for fmt in artifact.formats
            if (primary.parent / f"{base_name}.{fmt}").exists()
        ]

    @staticmethod
    def delete_files(artifact: GeneratedArtifact) -> None:
        """Best-effort removal of an artifact's rendered files.

        Refuses to touch anything that escapes the artifacts root, and removes
        the per-artifact directory once it is empty.

        Args:
            artifact: Artifact row whose files are removed.
        """
        primary = resolve_contained_artifact_path(artifact.output_path)
        if primary is None:
            if artifact.output_path:
                logger.warning(
                    f"Refusing to delete artifact file outside artifacts "
                    f"directory: {artifact.output_path}"
                )
            return

        base_name = primary.stem
        for fmt in artifact.formats:
            candidate = primary.parent / f"{base_name}.{fmt}"
            try:
                if candidate.exists():
                    candidate.unlink()
            except Exception as exc:
                logger.warning(f"Failed to delete artifact file {candidate}: {exc}")

        diagrams_dir = primary.parent / "diagrams"
        try:
            if diagrams_dir.is_dir():
                for image in diagrams_dir.iterdir():
                    if image.is_file():
                        image.unlink()
                diagrams_dir.rmdir()
        except Exception as exc:
            logger.warning(f"Failed to clean artifact diagrams dir: {exc}")

        try:
            if primary.parent.is_dir() and not any(primary.parent.iterdir()):
                primary.parent.rmdir()
        except Exception as exc:
            logger.warning(f"Failed to remove artifact directory: {exc}")

    @staticmethod
    def to_relative_path(absolute_path: str) -> str:
        """Expose the write-side path check for callers that need it.

        Args:
            absolute_path: Rendered file path.

        Returns:
            The path relative to ``ARTIFACTS_FOLDER``.
        """
        return to_relative_artifact_path(absolute_path)
