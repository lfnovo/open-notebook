"""
Surreal-commands command for async question paper generation.
Runs the slot-based LangGraph pipeline in the background.
"""

import time
from typing import Any, Dict, List, Optional

from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id, repo_update
from open_notebook.graphs.question_paper import question_paper_graph
from open_notebook.graphs.question_bank_batch import question_bank_batch_graph


class GeneratePaperInput(CommandInput):
    paper_id: str
    topic: str
    difficulty: str
    target_marks: int
    section_config: dict = {}
    curriculum_objectives: List[str] = []
    generator_model: Optional[str] = None
    reviewer_model: Optional[str] = None
    book_content: Optional[str] = None
    book_chapters: List[Dict[str, Any]] = []
    grade: Optional[str] = None
    subject: Optional[str] = None
    language: str = "en"
    pass_percentage: int = 70
    blueprint_preset: Optional[dict] = None
    max_slot_attempts: int = 3
    max_refill_attempts: int = 5
    slot_concurrency: int = 3


class GeneratePaperOutput(CommandOutput):
    success: bool
    paper_id: str
    processing_time: float
    question_count: int = 0
    error_message: Optional[str] = None


@command(
    "generate_question_paper",
    app="open_notebook",
    retry=None,  # No retry — idempotency would create duplicate papers
)
async def generate_question_paper_command(
    input_data: GeneratePaperInput,
) -> GeneratePaperOutput:
    """
    Run the question paper generation pipeline.

    Flow:
    1. Update paper status → 'running'
    2. Invoke slot-based LangGraph (prepare → fill_slots → assemble → coverage → audit → persist_bank)
    3. Persist final_paper + answer_key
    4. Status → 'completed' only if the deterministic blueprint audit passes
    """
    start_time = time.time()
    paper_id = input_data.paper_id

    try:
        logger.info(f"Starting question paper generation for {paper_id}")

        await repo_update(
            "question_paper",
            ensure_record_id(paper_id),
            {"status": "running"},
        )

        initial_state = {
            "topic": input_data.topic,
            "difficulty": input_data.difficulty,
            "target_marks": input_data.target_marks,
            "section_config": input_data.section_config or {},
            "curriculum_objectives": input_data.curriculum_objectives,
            "generator_model": input_data.generator_model,
            "reviewer_model": input_data.reviewer_model,
            "book_content": input_data.book_content,
            "book_chapters": input_data.book_chapters or [],
            "grade": input_data.grade or "",
            "subject": input_data.subject or input_data.topic,
            "language": input_data.language,
            "pass_percentage": input_data.pass_percentage,
            "blueprint_preset": input_data.blueprint_preset,
            "max_slot_attempts": input_data.max_slot_attempts,
            "max_refill_attempts": input_data.max_refill_attempts,
            "slot_concurrency": input_data.slot_concurrency,
            "used_stems": [],
            "raw_questions": [],
            "deduplicated": [],
            "approved": [],
            "rejected_with_feedback": [],
            "failed_slots": [],
            "final_paper": {},
            "answer_key": [],
            "coverage_gaps": [],
            "retry_count": 0,
            "covered_topics": [],
        }

        result = await question_paper_graph.ainvoke(
            initial_state,
            config={"recursion_limit": 20},
        )

        final_paper = result.get("final_paper", {})
        answer_key = result.get("answer_key", [])
        coverage_gaps = result.get("coverage_gaps", [])
        covered_topics = result.get("covered_topics", [])
        failed_slots = result.get("failed_slots", [])
        audit = result.get("audit") or {}
        question_count = final_paper.get("question_count", 0)
        audit_ok = bool(audit.get("ok"))
        status = "completed" if audit_ok else "needs_manual_review"
        error_message = None if audit_ok else "; ".join(audit.get("errors") or ["Blueprint audit failed"])

        import json as _json

        from open_notebook.database.repository import repo_query
        _fp_json = _json.dumps(final_paper)
        _ak_json = _json.dumps(answer_key)
        _cg_json = _json.dumps(coverage_gaps)
        _ct_json = _json.dumps(covered_topics)
        _fs_json = _json.dumps(failed_slots)
        _audit_json = _json.dumps(audit)
        # SurrealDB option<string> rejects JSON null; use NONE instead.
        _err_sql = "NONE" if error_message is None else _json.dumps(error_message)
        await repo_query(
            f"UPDATE {paper_id} MERGE "
            f"{{final_paper: {_fp_json}, answer_key: {_ak_json}, "
            f"coverage_gaps: {_cg_json}, covered_topics: {_ct_json}, "
            f"failed_slots: {_fs_json}, audit: {_audit_json}, "
            f"error_message: {_err_sql}, status: '{status}'}}",
            {},
        )
        logger.info(
            f"Saved paper {paper_id}: {question_count} questions status={status}"
        )

        processing_time = time.time() - start_time
        return GeneratePaperOutput(
            success=audit_ok,
            paper_id=paper_id,
            processing_time=processing_time,
            question_count=question_count,
            error_message=error_message,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Question paper generation failed for {paper_id}: {e}")
        logger.exception(e)

        try:
            await repo_update(
                "question_paper",
                ensure_record_id(paper_id),
                {"status": "failed", "error_message": str(e)},
            )
        except Exception as update_err:
            logger.error(f"Failed to update paper status to failed: {update_err}")

        return GeneratePaperOutput(
            success=False,
            paper_id=paper_id,
            processing_time=processing_time,
            error_message=str(e),
        )


class GenerateBankBatchInput(CommandInput):
    batch_id: str
    book_id: str
    grade: str
    subject: str
    chapter: int
    difficulty: str
    total_questions: int
    single_correct: int
    multiple_correct: int
    language: str = "en"
    book_content: Optional[str] = None
    book_chapters: List[Dict[str, Any]] = []
    curriculum_objectives: List[str] = []
    generator_model: Optional[str] = None
    reviewer_model: Optional[str] = None
    max_slot_attempts: int = 3
    max_refill_attempts: int = 5
    slot_concurrency: int = 3


class GenerateBankBatchOutput(CommandOutput):
    success: bool
    batch_id: str
    processing_time: float
    accepted: int = 0
    requested: int = 0
    status: str = "failed"
    error_message: Optional[str] = None


@command(
    "generate_question_bank_batch",
    app="open_notebook",
    retry=None,
)
async def generate_question_bank_batch_command(
    input_data: GenerateBankBatchInput,
) -> GenerateBankBatchOutput:
    """
    Run the Question Bank Batch pipeline.

    Flow:
    1. Update batch status → running
    2. Invoke bank-batch LangGraph (prepare → fill → refill → audit → persist)
    3. Persist audit + counts; status completed or completed_partial
    """
    import json as _json

    from open_notebook.database.repository import repo_query
    from open_notebook.graphs.question_paper_blueprint import bank_batch_from_dict

    start_time = time.time()
    batch_id = input_data.batch_id

    blueprint_dict = {
        "book_id": input_data.book_id,
        "grade": input_data.grade,
        "subject": input_data.subject,
        "chapter": input_data.chapter,
        "difficulty": input_data.difficulty,
        "total_questions": input_data.total_questions,
        "single_correct": input_data.single_correct,
        "multiple_correct": input_data.multiple_correct,
        "language": input_data.language,
    }

    try:
        logger.info(f"Starting question bank batch generation for {batch_id}")
        blueprint = bank_batch_from_dict(blueprint_dict)

        await repo_update(
            "question_bank_batch",
            ensure_record_id(batch_id),
            {"status": "running"},
        )

        initial_state = {
            "topic": input_data.subject,
            "subject": input_data.subject,
            "grade": input_data.grade,
            "language": input_data.language,
            "curriculum_objectives": input_data.curriculum_objectives,
            "generator_model": input_data.generator_model,
            "reviewer_model": input_data.reviewer_model,
            "book_content": input_data.book_content,
            "book_chapters": input_data.book_chapters or [],
            "max_slot_attempts": input_data.max_slot_attempts,
            "max_refill_attempts": input_data.max_refill_attempts,
            "slot_concurrency": input_data.slot_concurrency,
            "bank_batch_blueprint": blueprint_dict,
            "bank_batch_mode": True,
            "batch_id": batch_id,
            "book_id": input_data.book_id,
            "used_stems": [],
            "approved": [],
            "failed_slots": [],
            "rejected_with_feedback": [],
            "persisted_question_ids": [],
        }

        result = await question_bank_batch_graph.ainvoke(
            initial_state,
            config={"recursion_limit": 20},
        )

        audit = result.get("audit") or {}
        approved = result.get("approved") or []
        failed_slots = result.get("failed_slots") or []
        rejected_attempts = result.get("rejected_with_feedback") or []
        saved_ids = result.get("persisted_question_ids") or []
        status = audit.get("status") or (
            "completed" if len(approved) == blueprint.total_questions else "completed_partial"
        )
        requested = int(audit.get("requested") or blueprint.total_questions)
        accepted = int(audit.get("accepted") or len(approved))
        failed_count = int(audit.get("failed") or len(failed_slots))
        failure_summary = audit.get("failure_summary") or {}
        error_message = None
        if status == "completed_partial" and accepted < requested:
            error_message = (
                f"Generated {accepted}/{requested} high-quality questions; "
                f"{failed_count} slot(s) could not be finalized after bounded retries."
            )

        _audit_json = _json.dumps(audit)
        _fs_json = _json.dumps(failed_slots)
        _saved_json = _json.dumps(saved_ids)
        _summary_json = _json.dumps(failure_summary)
        _rejected_json = _json.dumps(rejected_attempts)
        _err_sql = "NONE" if error_message is None else _json.dumps(error_message)

        await repo_query(
            f"UPDATE {batch_id} MERGE "
            f"{{audit: {_audit_json}, failed_slots: {_fs_json}, "
            f"saved_question_ids: {_saved_json}, failure_summary: {_summary_json}, "
            f"rejected_attempts: {_rejected_json}, "
            f"requested: {requested}, accepted: {accepted}, failed: {failed_count}, "
            f"error_message: {_err_sql}, status: '{status}'}}",
            {},
        )

        logger.info(
            f"Saved bank batch {batch_id}: {accepted}/{requested} accepted status={status}"
        )

        processing_time = time.time() - start_time
        return GenerateBankBatchOutput(
            success=status in ("completed", "completed_partial") and accepted > 0,
            batch_id=batch_id,
            processing_time=processing_time,
            accepted=accepted,
            requested=requested,
            status=status,
            error_message=error_message,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Question bank batch generation failed for {batch_id}: {e}")
        logger.exception(e)

        try:
            await repo_update(
                "question_bank_batch",
                ensure_record_id(batch_id),
                {"status": "failed", "error_message": str(e)},
            )
        except Exception as update_err:
            logger.error(f"Failed to update bank batch status to failed: {update_err}")

        return GenerateBankBatchOutput(
            success=False,
            batch_id=batch_id,
            processing_time=processing_time,
            error_message=str(e),
        )
