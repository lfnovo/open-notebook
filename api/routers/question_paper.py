from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel, Field

from api.question_paper_service import (
    BookService,
    ExportBankXlsxRequest,
    GenerateBankBatchRequest,
    GenerateBankBatchResponse,
    GeneratePaperRequest,
    GeneratePaperResponse,
    QuestionPaperService,
)
from open_notebook.graphs.question_paper_blueprint import DEFAULT_PRESET

router = APIRouter()


class UpdateBookMetadataRequest(BaseModel):
    book_name: str = Field(..., min_length=1)
    year: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    subject: str = ""
    edition: str = ""
    display_name: str = ""


@router.get("/papers/blueprint/default")
async def get_default_blueprint():
    """Return the default Chapter × Difficulty / answer-type blueprint preset."""
    return DEFAULT_PRESET


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
    """Download a completed question paper as a CSV file (legacy)."""
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


@router.get("/papers/{paper_id}/export/xlsx")
async def export_paper_xlsx(paper_id: str):
    """Download as Excel (.xlsx) with QA review sheets."""
    try:
        xlsx_bytes = await QuestionPaperService.export_paper_xlsx(paper_id)
        safe_id = paper_id.replace(":", "_").replace("/", "_")
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="question_paper_{safe_id}.xlsx"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting paper xlsx {paper_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export paper as Excel")


@router.get("/papers/{paper_id}/export/docx")
async def export_paper_docx(paper_id: str):
    """Download as Word (.docx) — clean student paper format."""
    try:
        docx_bytes = await QuestionPaperService.export_paper_docx(paper_id)
        safe_id = paper_id.replace(":", "_").replace("/", "_")
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="question_paper_{safe_id}.docx"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting paper docx {paper_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export paper as Word")


@router.get("/papers/{paper_id}/export/txt")
async def export_paper_txt(paper_id: str):
    """Download as plain text with corrected metadata."""
    try:
        txt_bytes = await QuestionPaperService.export_paper_txt(paper_id)
        safe_id = paper_id.replace(":", "_").replace("/", "_")
        return Response(
            content=txt_bytes,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="question_paper_{safe_id}.txt"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting paper txt {paper_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export paper as text")


@router.post("/papers/{paper_id}/regenerate-missing")
async def regenerate_missing(paper_id: str):
    """Regenerate only the failed slots of a needs_manual_review paper."""
    try:
        return await QuestionPaperService.regenerate_missing(paper_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error regenerating missing for {paper_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate missing questions: {e}")


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


@router.get("/papers/bank/batches")
async def list_bank_batches():
    """List existing Question Bank Batch jobs (metadata only). Does not generate."""
    try:
        return await QuestionPaperService.list_bank_batches()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bank batches: {e}")
        raise HTTPException(status_code=500, detail="Failed to list bank batches")


@router.post("/papers/bank/batch/generate", response_model=GenerateBankBatchResponse)
async def generate_bank_batch(request: GenerateBankBatchRequest):
    """Submit an async Question Bank Batch generation job (single chapter × difficulty)."""
    try:
        return await QuestionPaperService.create_and_submit_bank_batch(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting bank batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit bank batch generation")


@router.get("/papers/bank/batch/{batch_id}/status")
async def get_bank_batch_status(batch_id: str):
    """Poll status of a Question Bank Batch job."""
    try:
        return await QuestionPaperService.get_bank_batch_status(batch_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bank batch status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bank batch status")


@router.get("/papers/bank/batch/{batch_id}/result")
async def get_bank_batch_result(batch_id: str):
    """Fetch result of a completed or partially completed bank batch."""
    try:
        return await QuestionPaperService.get_bank_batch_result(batch_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bank batch result: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bank batch result")


@router.get("/papers/bank/search")
async def search_question_bank(
    q: str = Query(default="", description="Search query"),
    limit: int = Query(default=1000, ge=1, le=2000),
):
    """Semantic/text search across the persistent question bank."""
    try:
        return await QuestionPaperService.search_bank(q, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching question bank: {e}")
        raise HTTPException(status_code=500, detail="Failed to search question bank")


@router.post("/papers/bank/export/xlsx")
async def export_question_bank_xlsx(request: ExportBankXlsxRequest):
    """Download currently selected Question Bank rows as Excel. Read-only."""
    try:
        xlsx_bytes = await QuestionPaperService.export_bank_xlsx(request.question_ids)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="question_bank.xlsx"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting question bank xlsx: {e}")
        raise HTTPException(status_code=500, detail="Failed to export question bank")


@router.get("/papers/books")
async def list_books():
    """List stored books for the Grade → Year → Book picker. Does not delete or alter records."""
    try:
        return await BookService.list_books()
    except Exception as e:
        logger.error(f"Error listing books: {e}")
        raise HTTPException(status_code=500, detail="Failed to list books")


@router.post("/papers/books/upload")
async def upload_book(
    file: UploadFile = File(...),
    book_name: str = Form(...),
    year: str = Form(...),
    grade: str = Form(...),
    subject: str = Form(""),
    edition: str = Form(""),
    display_name: str = Form(""),
):
    """
    Upload a PDF/book, extract text, detect chapters, and store reusable library metadata.
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
        return await BookService.upload_and_extract(
            file,
            book_name=book_name,
            year=year,
            grade=grade,
            subject=subject,
            edition=edition,
            display_name=display_name,
        )
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
        "SELECT id, title, book_name, year, grade, subject, edition, display_name, "
        "detected_grade, chapters, created FROM question_book WHERE id = $id",
        {"id": ensure_record_id(book_id)},
    )
    if not results:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookService.serialize_book(results[0], include_chapters=True)


@router.patch("/papers/books/{book_id}")
async def update_book_metadata(book_id: str, request: UpdateBookMetadataRequest):
    """Update saved-book labels only. Does not change book_id, text, or chapters."""
    try:
        return await BookService.update_metadata(
            book_id,
            book_name=request.book_name,
            year=request.year,
            grade=request.grade,
            subject=request.subject,
            edition=request.edition,
            display_name=request.display_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating book metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to update book details")


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
