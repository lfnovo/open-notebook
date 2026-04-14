"""
Service layer for question paper generation.
Handles paper creation, job submission, status tracking, and book upload.
"""

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel
from surreal_commands import get_command_status, submit_command

from open_notebook.database.repository import repo_create, repo_delete, repo_query
from open_notebook.domain.question_bank import QuestionPaper, QuestionRecord

# Register command module at import time so it's always available
try:
    import commands.question_paper_commands  # noqa: F401
except ImportError as e:
    logger.warning(f"Could not import question paper commands module: {e}")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class GeneratePaperRequest(BaseModel):
    topic: str
    difficulty: str = "medium"  # easy | medium | hard
    target_marks: int = 50
    section_config: dict = {"mcq": 10, "short": 5, "scenario": 3}
    curriculum_objectives: List[str] = []
    generator_model: Optional[str] = None
    reviewer_model: Optional[str] = None
    # Book-grounding (optional)
    book_id: Optional[str] = None
    selected_chapters: Optional[List[int]] = None  # chapter indices; None = all chapters


class GeneratePaperResponse(BaseModel):
    job_id: str
    paper_id: str
    status: str
    message: str
    topic: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class QuestionPaperService:

    @staticmethod
    async def create_and_submit(request: GeneratePaperRequest) -> GeneratePaperResponse:
        """Create a question_paper record and submit the generation job."""

        # 1. Validate inputs
        valid_difficulties = {"easy", "medium", "hard"}
        if request.difficulty not in valid_difficulties:
            raise HTTPException(
                status_code=400,
                detail=f"difficulty must be one of {sorted(valid_difficulties)}",
            )
        if request.target_marks < 5 or request.target_marks > 500:
            raise HTTPException(
                status_code=400,
                detail="target_marks must be between 5 and 500",
            )
        if not request.section_config:
            raise HTTPException(status_code=400, detail="section_config cannot be empty")
        if any(not isinstance(v, int) or v < 1 or v > 100 for v in request.section_config.values()):
            raise HTTPException(status_code=400, detail="section_config values must be positive integers")
        if not request.topic.strip():
            raise HTTPException(status_code=400, detail="topic cannot be empty")
        if request.book_id and request.selected_chapters is not None and len(request.selected_chapters) == 0:
            raise HTTPException(status_code=400, detail="selected_chapters cannot be empty; omit it to use all chapters")

        # 2. Create paper record (status=pending)
        paper_data = {
            "topic": request.topic.strip(),
            "difficulty": request.difficulty,
            "target_marks": request.target_marks,
            "section_config": request.section_config,
            "status": "pending",
        }
        raw_paper = await repo_create("question_paper", paper_data)
        if not raw_paper:
            raise HTTPException(status_code=500, detail="Failed to create paper record")
        paper_record = raw_paper[0] if isinstance(raw_paper, list) else raw_paper

        paper_id = str(paper_record["id"])

        # 3. Resolve book content if a book was provided
        book_content: Optional[str] = None
        if request.book_id:
            try:
                book_content = await QuestionPaperService.get_book_content(
                    request.book_id, request.selected_chapters
                )
            except Exception as e:
                logger.warning(f"Could not load book content: {e}")

        # 5. Submit generation job
        try:
            cmd_id = submit_command(
                "open_notebook",
                "generate_question_paper",
                {
                    "paper_id": paper_id,
                    "topic": request.topic.strip(),
                    "difficulty": request.difficulty,
                    "target_marks": request.target_marks,
                    "section_config": request.section_config,
                    "curriculum_objectives": request.curriculum_objectives,
                    "generator_model": request.generator_model,
                    "reviewer_model": request.reviewer_model,
                    "book_content": book_content,
                },
            )
        except Exception as e:
            logger.error(f"Failed to submit question paper job: {e}")
            raise HTTPException(status_code=500, detail="Failed to submit generation job")

        cmd_id_str = str(cmd_id)

        # 6. Store command reference on paper record using raw SurrealQL
        # The command field is option<record> — must use a record link literal in SurrealQL,
        # not a plain string or RecordID object passed via MERGE.
        from open_notebook.database.repository import repo_query, ensure_record_id
        try:
            await repo_query(
                f"UPDATE {paper_id} SET command = {cmd_id_str}",
                {},
            )
        except Exception as e:
            # Non-fatal: job was already submitted; log and continue
            logger.warning(f"Could not store command reference on paper {paper_id}: {e}")

        logger.info(f"Submitted question paper job {cmd_id_str} for paper {paper_id}")

        return GeneratePaperResponse(
            job_id=cmd_id_str,
            paper_id=paper_id,
            status="submitted",
            message=f"Question paper generation started for topic '{request.topic}'",
            topic=request.topic,
        )

    @staticmethod
    async def get_paper_status(paper_id: str) -> Dict[str, Any]:
        """Get status of a question paper by its record ID."""
        from open_notebook.database.repository import ensure_record_id
        results = await repo_query(
            "SELECT * FROM question_paper WHERE id = $id",
            {"id": ensure_record_id(paper_id)},
        )
        if not results:
            raise HTTPException(status_code=404, detail="Paper not found")

        paper = results[0]
        paper_status = paper.get("status", "unknown")
        job_status = None

        command_id = paper.get("command")
        if command_id:
            try:
                cmd = await get_command_status(str(command_id))
                if cmd:
                    job_status = cmd.status
                    # Sync failed status from command back to DB if not already recorded
                    if cmd.status in ("failed", "error") and paper_status not in ("failed", "error"):
                        paper_status = "failed"
                        from open_notebook.database.repository import repo_update
                        try:
                            await repo_update(
                                "question_paper",
                                ensure_record_id(paper_id),
                                {"status": "failed", "error_message": "Job execution failed"},
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Failed to get command status for {command_id}: {e}")

        return {
            "paper_id": str(paper.get("id", paper_id)),
            "status": paper_status,
            "job_status": job_status,
            "topic": paper.get("topic", ""),
            "difficulty": paper.get("difficulty", ""),
            "target_marks": paper.get("target_marks", 0),
            "error_message": paper.get("error_message"),
            "created": str(paper.get("created", "")),
        }

    @staticmethod
    async def get_paper_result(paper_id: str) -> Dict[str, Any]:
        """Fetch a completed paper result."""
        from open_notebook.database.repository import ensure_record_id
        results = await repo_query(
            "SELECT * FROM question_paper WHERE id = $id",
            {"id": ensure_record_id(paper_id)},
        )
        if not results:
            raise HTTPException(status_code=404, detail="Paper not found")

        paper = results[0]
        if paper.get("status") not in ("completed",):
            raise HTTPException(
                status_code=409,
                detail=f"Paper is not yet completed (status: {paper.get('status')})",
            )

        return {
            "paper_id": str(paper.get("id", paper_id)),
            "topic": paper.get("topic", ""),
            "difficulty": paper.get("difficulty", ""),
            "target_marks": paper.get("target_marks", 0),
            "section_config": paper.get("section_config", {}),
            "final_paper": paper.get("final_paper", {}),
            "answer_key": paper.get("answer_key", []),
            "coverage_gaps": paper.get("coverage_gaps", []),
            "covered_topics": paper.get("covered_topics", []),
            "status": paper.get("status", ""),
            "created": str(paper.get("created", "")),
        }

    @staticmethod
    async def list_papers() -> List[Dict[str, Any]]:
        """List all question papers (metadata only, no content)."""
        results = await repo_query(
            "SELECT id, topic, difficulty, target_marks, section_config, status, "
            "error_message, created FROM question_paper ORDER BY created DESC LIMIT 50"
        )
        return [
            {
                "paper_id": str(r.get("id", "")),
                "topic": r.get("topic", ""),
                "difficulty": r.get("difficulty", ""),
                "target_marks": r.get("target_marks", 0),
                "section_config": r.get("section_config", {}),
                "status": r.get("status", ""),
                "error_message": r.get("error_message"),
                "created": str(r.get("created", "")),
            }
            for r in (results or [])
        ]

    @staticmethod
    async def delete_paper(paper_id: str) -> None:
        """Delete a question paper record."""
        from open_notebook.database.repository import ensure_record_id
        try:
            await repo_delete(ensure_record_id(paper_id))
        except Exception as e:
            logger.error(f"Failed to delete paper {paper_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete paper")

    @staticmethod
    async def search_bank(query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Text search across the question bank."""
        if not query.strip():
            results = await repo_query(
                "SELECT id, question, topic, type, difficulty, answer FROM question_bank "
                "ORDER BY created DESC LIMIT $limit",
                {"limit": limit},
            )
        else:
            results = await repo_query(
                "SELECT id, question, topic, type, difficulty, answer FROM question_bank "
                "WHERE string::contains(string::lowercase(question), string::lowercase($q)) "
                "OR string::contains(string::lowercase(topic), string::lowercase($q)) "
                "LIMIT $limit",
                {"q": query.strip(), "limit": limit},
            )
        return [
            {
                "id": str(r.get("id", "")),
                "question": r.get("question", ""),
                "topic": r.get("topic", ""),
                "type": r.get("type", ""),
                "difficulty": r.get("difficulty", ""),
                "answer": r.get("answer", ""),
            }
            for r in (results or [])
        ]

    @staticmethod
    async def delete_bank_question(question_id: str) -> None:
        """Remove a question from the bank."""
        from open_notebook.database.repository import ensure_record_id
        try:
            await repo_delete(ensure_record_id(question_id))
        except Exception as e:
            logger.error(f"Failed to delete question {question_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete question")

    # ------------------------------------------------------------------
    # Book upload helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_book_content(book_id: str, selected_chapters: Optional[List[int]]) -> str:
        """Fetch book text for selected chapters (or full text if none selected)."""
        from open_notebook.database.repository import ensure_record_id
        results = await repo_query(
            "SELECT * FROM question_book WHERE id = $id",
            {"id": ensure_record_id(book_id)},
        )
        if not results:
            raise HTTPException(status_code=404, detail="Book not found")
        book = results[0]
        chapters: List[dict] = book.get("chapters", [])

        if not chapters or selected_chapters is None:
            return book.get("full_text", "")

        # Splice out only selected chapters by character offsets
        full_text: str = book.get("full_text", "")
        parts = []
        for idx in selected_chapters:
            if 0 <= idx < len(chapters):
                ch = chapters[idx]
                start = ch.get("start_char", 0)
                end = ch.get("end_char", len(full_text))
                parts.append(full_text[start:end])
        return "\n\n".join(parts) if parts else full_text


class BookService:
    """Handles book upload, text extraction, and chapter detection."""

    @staticmethod
    async def upload_and_extract(upload_file: UploadFile) -> Dict[str, Any]:
        """
        Save the file, extract full text via content_core, detect chapters.
        Returns book record with chapter list.
        """
        from content_core import extract_content
        from open_notebook.config import UPLOADS_FOLDER

        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # 1. Save to uploads folder
        safe_name = re.sub(r"[^\w\-_\. ]", "_", upload_file.filename)
        dest = os.path.join(UPLOADS_FOLDER, safe_name)
        # Make unique
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1

        try:
            content = await upload_file.read()
            with open(dest, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        # 2. Extract text — content_core expects a state dict and is async
        try:
            from content_core import extract_content
            content_state = {
                "file_path": dest,
                "document_engine": "auto",
                "output_format": "markdown",
                "delete_source": False,
            }
            processed = await extract_content(content_state)
            # extract_content returns a ProcessSourceState object; .content holds the text
            full_text: str = getattr(processed, "content", "") or ""
            if not full_text:
                # fallback: try dict-style access
                full_text = processed.get("content", "") if isinstance(processed, dict) else ""
        except Exception as e:
            logger.error(f"content_core extraction failed: {e}")
            # Plain-text fallback for .txt / .md files
            try:
                with open(dest, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
            except Exception:
                raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")

        if not full_text.strip():
            raise HTTPException(status_code=422, detail="Could not extract any text from the file")

        # 3. Detect chapters
        chapters = BookService._detect_chapters(full_text)

        # 4. Store in DB
        title = os.path.splitext(upload_file.filename)[0]
        raw = await repo_create("question_book", {
            "title": title,
            "file_path": dest,
            "full_text": full_text,
            "chapters": chapters,
        })
        record = raw[0] if isinstance(raw, list) else raw

        return {
            "book_id": str(record["id"]),
            "title": title,
            "total_chars": len(full_text),
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

    @staticmethod
    def _detect_chapters(text: str) -> List[Dict[str, Any]]:
        """
        Hierarchical chapter detection tried in order of specificity.

        Strategy 1 — explicit keyword  ("Chapter 1 / Chapter I"):       min 3000 chars
        Strategy 2 — pipe format       ("1 | Title"):                   min 2000 chars
        Strategy 3 — Markdown H1       ("# Title"):                     min 2000 chars
        Strategy 4 — isolated numbered ("1. Title" preceded by blank):  min 3000 chars
        Strategy 5 — Markdown H2       ("## Title"):                    min 1000 chars
        Strategy 6 — subsection num    ("1.1 Title"):                   min  500 chars
        Fallback   — equal-size chunks

        Each strategy is tried independently. The first one that yields >= 2 chapters wins.
        Numbered list items (e.g. "5. The British Pound Sterling:") are excluded from
        strategy 4 by requiring a blank line before the heading.
        """

        def _has_blank_line_before(pos: int) -> bool:
            """Return True if the character before pos is preceded by a blank line."""
            before = text[:pos]
            last_nl = before.rfind("\n")
            if last_nl == -1:
                return True  # start of file
            second_nl = before.rfind("\n", 0, last_nl)
            if second_nl == -1:
                return pos < 10  # very near start of file
            between = before[second_nl + 1 : last_nl].strip()
            return len(between) == 0

        def _filter_matches(matches: list, min_chars: int, require_blank_before: bool = False) -> list:
            kept = []
            for i, m in enumerate(matches):
                if require_blank_before and not _has_blank_line_before(m.start()):
                    continue
                next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                if (next_start - m.end()) >= min_chars:
                    kept.append(m)
            return kept

        def _build_chapters(matches: list) -> List[Dict[str, Any]]:
            chapters = []
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                chapter_text = text[start:end].strip()
                heading = next(g for g in match.groups() if g is not None).strip()
                preview = chapter_text[:200].replace("\n", " ").strip()
                chapters.append({
                    "index": i,
                    "title": heading[:120],
                    "start_char": start,
                    "end_char": end,
                    "preview": preview,
                })
            return chapters

        def _try(pattern_str: str, flags: int, min_chars: int, require_blank: bool = False) -> List[Dict[str, Any]]:
            matches = list(re.finditer(pattern_str, text, flags))
            filtered = _filter_matches(matches, min_chars, require_blank_before=require_blank)
            if len(filtered) >= 2:
                return _build_chapters(filtered)
            return []

        # Strategy 1: explicit chapter keyword — most reliable
        result = _try(
            r"^((?:chapter|unit|section|part|module|lesson)\s+[\divxlcdmIVXLCDM]+[\.\s:—\-]*[^\n]{0,80})",
            re.MULTILINE | re.IGNORECASE,
            min_chars=3000,
        )
        if result:
            return result

        # Strategy 2: pipe-delimited "1 | Title" — common in textbooks/workbooks
        result = _try(
            r"^(\d{1,2}\s*[|｜]\s+[A-Z][^\n]{2,60})$",
            re.MULTILINE,
            min_chars=2000,
        )
        if result:
            return result

        # Strategy 3: Markdown H1
        result = _try(
            r"^(#\s+[^\n]{3,80})",
            re.MULTILINE,
            min_chars=2000,
        )
        if result:
            return result

        # Strategy 4: isolated numbered heading "1. Title" — REQUIRE blank line before
        # to avoid matching items inside numbered lists.
        result = _try(
            r"^(\d{1,2}\.\s+[A-Z][^\n]{5,60})$",
            re.MULTILINE,
            min_chars=3000,
            require_blank=True,
        )
        if result:
            return result

        # Strategy 5: Markdown H2
        result = _try(
            r"^(#{1,2}\s+[^\n]{3,80})",
            re.MULTILINE,
            min_chars=1000,
        )
        if result:
            return result

        # Strategy 6: subsection numbering "1.1 Title"
        result = _try(
            r"^(\d{1,2}\.\d+\s+[A-Z][^\n]{5,60})$",
            re.MULTILINE,
            min_chars=500,
        )
        if result:
            return result

        # Fallback: equal-size chunks
        return BookService._chunk_fallback(text)

    @staticmethod
    def _chunk_fallback(text: str, chunk_size: int = 5000) -> List[Dict[str, Any]]:
        """Split text into equal chunks when no chapter structure is detected."""
        chunks = []
        for i, start in enumerate(range(0, len(text), chunk_size)):
            end = min(start + chunk_size, len(text))
            snippet = text[start:end].strip()
            chunks.append({
                "index": i,
                "title": f"Part {i + 1}",
                "start_char": start,
                "end_char": end,
                "preview": snippet[:200].replace("\n", " "),
            })
        return chunks
