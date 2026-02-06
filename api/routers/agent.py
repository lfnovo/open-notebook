from typing import Any, Dict, List, Optional
import os
import httpx
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from open_notebook.acm_agent_service import get_research_agent
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.database.repository import ensure_record_id
from api.command_service import CommandService
from commands.source_commands import SourceProcessingInput

router = APIRouter()

# --- Helpers ---

def generate_unique_filename(original_filename: str, upload_folder: str) -> str:
    """Generate unique filename to avoid overwrites."""
    file_path = Path(upload_folder)
    file_path.mkdir(parents=True, exist_ok=True)

    # Split filename and extension
    stem = Path(original_filename).stem
    suffix = Path(original_filename).suffix

    # Check if file exists and generate unique name
    counter = 0
    while True:
        if counter == 0:
            new_filename = original_filename
        else:
            new_filename = f"{stem} ({counter}){suffix}"

        full_path = file_path / new_filename
        if not full_path.exists():
            return str(full_path)
        counter += 1

# --- Data Models ---

class PaperResult(BaseModel):
    title: str
    year: Optional[int] = None
    venue: str
    citations: Optional[int] = None
    pdf_url: str
    openalex_id: Optional[str] = None
    abstract_index: bool = False

class SearchPapersResponse(BaseModel):
    count: int
    results: List[PaperResult]

class IngestPaperRequest(BaseModel):
    pdf_url: str = Field(..., description="Direct URL to the paper PDF")
    notebook_id: str = Field(..., description="Target notebook ID to ingest into")
    title: Optional[str] = Field(None, description="Title of the paper")

class IngestPaperResponse(BaseModel):
    success: bool
    message: str
    source_id: Optional[str] = None
    command_id: Optional[str] = None

# --- Endpoints ---

@router.get("/agent/acm/search", response_model=SearchPapersResponse)
async def search_acm_papers(
    query: str = Query(..., min_length=3, description="Search query for ACM papers"),
    limit: int = Query(5, ge=1, le=20, description="Max results to return")
):
    """
    Search for Open Access papers in ACM Digital Library via OpenAlex.
    """
    try:
        agent = get_research_agent()
        results = agent.search_papers(query, limit=limit)
        
        # Convert dicts to Pydantic models
        papers = []
        for r in results:
            papers.append(PaperResult(
                title=r.get("title", "Untitled"),
                year=r.get("year"),
                venue=r.get("venue", "Unknown"),
                citations=r.get("citations"),
                pdf_url=r.get("pdf_url"),
                openalex_id=r.get("openalex_id"),
                abstract_index=r.get("abstract_index", False)
            ))
            
        return SearchPapersResponse(
            count=len(papers),
            results=papers
        )
    except Exception as e:
        logger.error(f"Error searching ACM papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/acm/ingest", response_model=IngestPaperResponse)
async def ingest_acm_paper(request: IngestPaperRequest):
    """
    Download a paper from URL and ingest it into the specified notebook.
    This triggers the standard source processing pipeline.
    """
    file_path = None
    try:
        # 1. Validate Notebook
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # 2. Download the PDF
        logger.info(f"Downloading paper from: {request.pdf_url}")
        
        # Extract filename from URL or use title
        filename = request.pdf_url.split('/')[-1]
        if not filename.lower().endswith('.pdf'):
            filename += ".pdf"
        
        # Use httpx for async download
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(request.pdf_url)
            response.raise_for_status()
            
            # Save to UPLOADS_FOLDER with unique name
            file_path = generate_unique_filename(filename, UPLOADS_FOLDER)
            
            # Write file (sync I/O is okay for small files, or could use aiofiles if strictly needed)
            with open(file_path, 'wb') as f:
                f.write(response.content)
                
        logger.info(f"Paper saved to: {file_path}")

        # 3. Create Source Record
        source_title = request.title or filename
        source = Source(
            title=source_title,
            topics=[],
        )
        await source.save()
        
        # Link to Notebook
        await source.add_to_notebook(request.notebook_id)

        # 4. Trigger Processing Command (Async)
        # Import command modules to ensure they're registered
        import commands.source_commands  # noqa: F401

        content_state = {
            "file_path": file_path,
            "delete_source": False # Keep file after processing
        }

        command_input = SourceProcessingInput(
            source_id=str(source.id),
            content_state=content_state,
            notebook_ids=[request.notebook_id],
            transformations=[], # No extra transformations for now
            embed=True, # Always embed for RAG
        )

        command_id = await CommandService.submit_command_job(
            "open_notebook",  # app name
            "process_source",  # command name
            command_input.model_dump(),
        )

        # Update source with command reference
        source.command = ensure_record_id(command_id)
        await source.save()
        
        return IngestPaperResponse(
            success=True,
            message="Paper downloaded and processing started",
            source_id=str(source.id),
            command_id=command_id
        )

    except httpx.HTTPError as e:
        logger.error(f"Download failed: {e}")
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to download paper: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error ingesting ACM paper: {e}")
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=str(e))

