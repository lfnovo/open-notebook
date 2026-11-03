"""Sections: the top level of section > folder > notebook."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import SectionDeleteResponse, SectionRequest, SectionResponse
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Section
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
    OpenNotebookError,
)

router = APIRouter()

MAX_SECTION_NAME_LENGTH = 80


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise InvalidInputError("Section name cannot be empty")
    if len(name) > MAX_SECTION_NAME_LENGTH:
        raise InvalidInputError(
            f"Section name cannot be longer than {MAX_SECTION_NAME_LENGTH} characters"
        )
    return name


async def _assert_name_free(name: str, exclude_id: Optional[str] = None) -> None:
    rows = await repo_query("SELECT id, name FROM section")
    wanted = name.casefold()
    for row in rows:
        if exclude_id and str(row.get("id")) == exclude_id:
            continue
        if str(row.get("name", "")).strip().casefold() == wanted:
            raise HTTPException(
                status_code=409, detail=f"A section named '{name}' already exists"
            )


async def _get_section(section_id: str) -> Section:
    # Section.get() resolves by id prefix, so guard against ids of other tables.
    try:
        section = await Section.get(section_id)
    except InvalidInputError:
        raise NotFoundError(f"section {section_id} not found") from None
    if not isinstance(section, Section):
        raise NotFoundError(f"section {section_id} not found")
    return section


def _response(section: Section, folder_count: int = 0) -> SectionResponse:
    return SectionResponse(
        id=section.id or "",
        name=section.name,
        created=str(section.created),
        updated=str(section.updated),
        folder_count=folder_count,
    )


async def _folder_count(section_id: str) -> int:
    rows = await repo_query(
        "SELECT count() AS n FROM folder WHERE section = $section GROUP ALL",
        {"section": ensure_record_id(section_id)},
    )
    return int(rows[0].get("n", 0)) if rows else 0


@router.get("/sections", response_model=List[SectionResponse])
async def get_sections():
    """List sections sorted by name, with their folder counts."""
    try:
        sections = await repo_query(
            "SELECT *, count(SELECT id FROM folder WHERE section = $parent.id) "
            "AS folder_count FROM section"
        )
        sections.sort(key=lambda s: (str(s.get("name", "")).casefold(), str(s["id"])))
        return [
            SectionResponse(
                id=str(s.get("id", "")),
                name=s.get("name", ""),
                created=str(s.get("created", "")),
                updated=str(s.get("updated", "")),
                folder_count=s.get("folder_count", 0),
            )
            for s in sections
        ]
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching sections: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sections: {e}")


@router.post("/sections", response_model=SectionResponse)
async def create_section(body: SectionRequest):
    """Create a section. 409 if the name exists (case-insensitive)."""
    try:
        name = _clean_name(body.name)
        await _assert_name_free(name)
        section = Section(name=name)
        await section.save()
        return _response(section)
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error creating section: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating section: {e}")


@router.put("/sections/{section_id}", response_model=SectionResponse)
async def rename_section(section_id: str, body: SectionRequest):
    """Rename a section. 409 if another section has the name (case-insensitive)."""
    try:
        section = await _get_section(section_id)
        name = _clean_name(body.name)
        await _assert_name_free(name, exclude_id=section.id)
        section.name = name
        await section.save()
        return _response(section, await _folder_count(section_id))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Section not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error renaming section {section_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error renaming section: {e}")


@router.delete("/sections/{section_id}", response_model=SectionDeleteResponse)
async def delete_section(section_id: str):
    """Delete a section. Its folders are kept and become unsectioned."""
    try:
        section = await _get_section(section_id)
        record = ensure_record_id(section_id)
        ungrouped = await repo_query(
            "UPDATE folder SET section = NONE WHERE section = $section RETURN id",
            {"section": record},
        )
        await section.delete()
        return SectionDeleteResponse(
            message="Section deleted successfully",
            folders_ungrouped=len(ungrouped),
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Section not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting section {section_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting section: {e}")
