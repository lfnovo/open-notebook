from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from loguru import logger

from api.question_paper_service import (
    BookService,
    GeneratePaperRequest,
    GeneratePaperResponse,
    QuestionPaperService,
)

router = APIRouter()


@router.post("/papers/generate", response_model=GeneratePaperResponse)
async def generate_paper(request: GeneratePaperRequest):
    """Submit a question paper generation job. Returns immediately with job + paper IDs."""
    try:
        return await QuestionPaperService.create_and_submit(request)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error generating question paper: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to start paper generation: {e}")


@router.get("/papers")
async def list_papers():
    """List all question papers (metadata only)."""
    try:
        return await QuestionPaperService.list_papers()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing papers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list papers")


@router.get("/papers/{paper_id}/status")
async def get_paper_status(paper_id: str):
    """Poll the status of a question paper generation job."""
    try:
        return await QuestionPaperService.get_paper_status(paper_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paper status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get paper status")


@router.get("/papers/{paper_id}/result")
async def get_paper_result(paper_id: str):
    """Fetch the completed paper + answer key. Returns 409 if not yet complete."""
    try:
        return await QuestionPaperService.get_paper_result(paper_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching paper result: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch paper result")


@router.get("/papers/{paper_id}/export")
async def export_paper_csv(paper_id: str):
    """Download a completed question paper as a CSV file (Excel-compatible)."""
    try:
        csv_bytes = await QuestionPaperService.export_paper_csv(paper_id)
        safe_id = paper_id.replace(":", "_").replace("/", "_")
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="question_paper_{safe_id}.csv"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export paper")


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a question paper record."""
    try:
        await QuestionPaperService.delete_paper(paper_id)
        return {"message": "Paper deleted", "paper_id": paper_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting paper: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete paper")


@router.get("/papers/bank/search")
async def search_question_bank(
    q: str = Query(default="", description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Semantic/text search across the persistent question bank."""
    try:
        return await QuestionPaperService.search_bank(q, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching question bank: {e}")
        raise HTTPException(status_code=500, detail="Failed to search question bank")


@router.post("/papers/books/upload")
async def upload_book(file: UploadFile = File(...)):
    """
    Upload a PDF/book, extract text, detect chapters.
    Returns book_id + chapter list. Frontend then lets user pick chapters before generating.
    """
    allowed_types = {
        "application/pdf",
        "text/plain",
        "application/epub+zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/markdown",
        "text/x-markdown",
    }
    if file.content_type and file.content_type not in allowed_types:
        # Allow by extension too — content_type can be wrong from browser
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in {"pdf", "txt", "epub", "docx", "doc", "md"}:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {file.content_type}. Upload a PDF, EPUB, DOCX, or TXT file.",
            )
    try:
        return await BookService.upload_and_extract(file)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing book upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")


@router.get("/papers/books/{book_id}")
async def get_book(book_id: str):
    """Get book metadata and chapter list."""
    from open_notebook.database.repository import ensure_record_id, repo_query
    results = await repo_query(
        "SELECT id, title, chapters, created FROM question_book WHERE id = $id",
        {"id": ensure_record_id(book_id)},
    )
    if not results:
        raise HTTPException(status_code=404, detail="Book not found")
    b = results[0]
    chapters = b.get("chapters", [])
    return {
        "book_id": str(b["id"]),
        "title": b.get("title", ""),
        "chapters": [
            {
                "index": ch["index"],
                "title": ch["title"],
                "preview": ch.get("preview", ""),
                "char_count": ch.get("end_char", 0) - ch.get("start_char", 0),
            }
            for ch in chapters
        ],
    }


@router.delete("/papers/books/{book_id}")
async def delete_book(book_id: str):
    """Delete an uploaded book record."""
    from open_notebook.database.repository import ensure_record_id, repo_delete, repo_query
    results = await repo_query(
        "SELECT file_path FROM question_book WHERE id = $id",
        {"id": ensure_record_id(book_id)},
    )
    if results and results[0].get("file_path"):
        import os
        try:
            os.unlink(results[0]["file_path"])
        except Exception:
            pass
    try:
        await repo_delete(ensure_record_id(book_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete book")
    return {"message": "Book deleted", "book_id": book_id}


@router.delete("/papers/bank/{question_id}")
async def delete_bank_question(question_id: str):
    """Remove a question from the persistent bank."""
    try:
        await QuestionPaperService.delete_bank_question(question_id)
        return {"message": "Question deleted", "question_id": question_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bank question: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete question")
