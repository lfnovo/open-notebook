"""Generated artifacts API (#203 artifacts tab).

Thin router over ``api/artifact_service.py``: submit a generation job, list
and inspect the results, download a rendered file, delete an artifact. The
generation itself runs in the background worker (``generate_artifact``), so
``POST /api/artifacts`` answers ``202`` immediately with the ids to poll -
the same shape as the podcast endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field

from api.artifact_service import ArtifactService
from open_notebook.artifacts.paths import resolve_contained_artifact_path
from open_notebook.domain.artifact import GeneratedArtifact
from open_notebook.exceptions import OpenNotebookError

router = APIRouter()

#: Media types for the formats ``render.py`` can produce.
MEDIA_TYPES = {
    "md": "text/markdown",
    "html": "text/html",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class ArtifactGenerationRequest(BaseModel):
    """Request body for ``POST /api/artifacts``."""

    notebook_id: str
    kind: str = "report"
    variant: Optional[str] = None
    formats: List[str] = Field(default_factory=lambda: ["md", "docx"])
    language: str = "en"
    title: Optional[str] = None
    instructions: Optional[str] = None
    sections: int = 5
    model_id: Optional[str] = None


class ArtifactSubmissionResponse(BaseModel):
    """``202`` payload: the ids the frontend polls."""

    command_id: str
    artifact_id: str
    status: str = "submitted"


class ArtifactResponse(BaseModel):
    """One artifact row plus its derived download information."""

    id: str
    notebook_id: str
    title: str
    kind: str
    variant: Optional[str] = None
    formats: List[str]
    language: str
    sections: int
    output_path: Optional[str] = None
    note_id: Optional[str] = None
    created: Optional[str] = None
    job_status: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    files: List[str] = Field(default_factory=list)


def _to_response(
    artifact: GeneratedArtifact,
    job_status: Optional[str],
    error_message: Optional[str],
) -> ArtifactResponse:
    """Build the API representation of one artifact.

    Args:
        artifact: Stored artifact row.
        job_status: Status of the generating job, when known.
        error_message: Job error, when the job failed.

    Returns:
        The response model, with the formats that exist on disk.
    """
    files = ArtifactService.available_files(artifact)
    artifact_id = str(artifact.id)
    return ArtifactResponse(
        id=artifact_id,
        notebook_id=str(artifact.notebook or ""),
        title=artifact.title,
        kind=artifact.kind,
        variant=artifact.variant,
        formats=list(artifact.formats),
        language=artifact.language,
        sections=artifact.sections,
        output_path=artifact.output_path,
        note_id=str(artifact.note_id) if artifact.note_id else None,
        created=str(artifact.created) if artifact.created else None,
        job_status=job_status,
        error_message=error_message,
        download_url=f"/api/artifacts/{artifact_id}/download" if files else None,
        files=files,
    )


async def _describe(artifact: GeneratedArtifact) -> ArtifactResponse:
    """Load the job status and build the API representation.

    Args:
        artifact: Stored artifact row.

    Returns:
        The response model.
    """
    status = await ArtifactService.get_job_status(
        str(artifact.command) if artifact.command else None
    )
    return _to_response(artifact, status["status"], status["error_message"])


@router.post("/artifacts", response_model=ArtifactSubmissionResponse, status_code=202)
async def generate_artifact(request: ArtifactGenerationRequest):
    """Submit an artifact generation job and return immediately."""
    try:
        result = await ArtifactService.submit_generation_job(
            notebook_id=request.notebook_id,
            kind=request.kind,
            formats=request.formats,
            language=request.language,
            title=request.title,
            instructions=request.instructions,
            sections=request.sections,
            model_id=request.model_id,
            variant=request.variant,
        )
        return ArtifactSubmissionResponse(
            command_id=result["command_id"], artifact_id=result["artifact_id"]
        )
    except HTTPException:
        raise
    except ValueError as e:
        # A variant that does not belong to the requested kind is a bad request,
        # not a server failure.
        logger.warning(f"Invalid artifact request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error submitting artifact generation: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to submit artifact generation"
        )


@router.get("/artifacts", response_model=List[ArtifactResponse])
async def list_artifacts(notebook_id: Optional[str] = Query(default=None)):
    """List artifacts, newest first, optionally scoped to a notebook."""
    try:
        artifacts = await ArtifactService.list_artifacts(notebook_id)
        return [await _describe(artifact) for artifact in artifacts]
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error listing artifacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str):
    """Return one artifact with its job status (used for polling)."""
    try:
        artifact = await ArtifactService.get_artifact(artifact_id)
        return await _describe(artifact)
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching artifact {artifact_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Artifact not found")


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str, format: Optional[str] = Query(default=None)
):
    """Download one rendered file of an artifact."""
    try:
        artifact = await ArtifactService.get_artifact(artifact_id)
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching artifact for download: {str(e)}")
        raise HTTPException(status_code=404, detail="Artifact not found")

    if not artifact.output_path:
        raise HTTPException(status_code=404, detail="Artifact has no file yet")

    primary = resolve_contained_artifact_path(artifact.output_path)
    if primary is None:
        logger.warning(
            f"Blocked artifact download outside artifacts directory for "
            f"{artifact_id}: {artifact.output_path}"
        )
        raise HTTPException(status_code=403, detail="Access to file denied")

    target = primary
    if format and format != primary.suffix.lstrip("."):
        candidate = primary.parent / f"{primary.stem}.{format}"
        if not candidate.exists():
            raise HTTPException(
                status_code=404, detail=f"Format '{format}' is not available"
            )
        target = candidate

    if not target.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")

    return FileResponse(
        target,
        media_type=MEDIA_TYPES.get(
            target.suffix.lstrip("."), "application/octet-stream"
        ),
        filename=target.name,
    )


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """Delete an artifact row and its rendered files."""
    try:
        artifact = await ArtifactService.get_artifact(artifact_id)
        ArtifactService.delete_files(artifact)
        await artifact.delete()
        logger.info(f"Deleted artifact: {artifact_id}")
        return {"message": "Artifact deleted successfully", "artifact_id": artifact_id}
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting artifact {artifact_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete artifact")
