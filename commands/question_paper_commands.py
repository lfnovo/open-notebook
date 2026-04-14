"""
Surreal-commands command for async question paper generation.
Runs the full 5-agent LangGraph pipeline in the background.
"""

import time
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id, repo_update
from open_notebook.domain.question_bank import QuestionPaper
from open_notebook.graphs.question_paper import question_paper_graph


class GeneratePaperInput(CommandInput):
    paper_id: str
    topic: str
    difficulty: str
    target_marks: int
    section_config: dict
    curriculum_objectives: List[str] = []
    generator_model: Optional[str] = None
    reviewer_model: Optional[str] = None
    book_content: Optional[str] = None


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
    Run the full question paper generation pipeline.

    Flow:
    1. Update paper status → 'running'
    2. Invoke 5-agent LangGraph pipeline
    3. Persist final_paper + answer_key to question_paper record
    4. Update status → 'completed' or 'failed'
    """
    start_time = time.time()
    paper_id = input_data.paper_id

    try:
        logger.info(f"Starting question paper generation for {paper_id}")

        # 1. Mark as running
        await repo_update(
            "question_paper",
            ensure_record_id(paper_id),
            {"status": "running"},
        )

        # 2. Build initial state
        initial_state = {
            "topic": input_data.topic,
            "difficulty": input_data.difficulty,
            "target_marks": input_data.target_marks,
            "section_config": input_data.section_config,
            "curriculum_objectives": input_data.curriculum_objectives,
            "generator_model": input_data.generator_model,
            "reviewer_model": input_data.reviewer_model,
            "book_content": input_data.book_content,
            "used_stems": [],
            "raw_questions": [],
            "deduplicated": [],
            "approved": [],
            "rejected_with_feedback": [],
            "final_paper": {},
            "answer_key": [],
            "coverage_gaps": [],
            "retry_count": 0,
            "covered_topics": [],
        }

        # 3. Run pipeline — increase recursion limit to support up to 8 retry rounds
        # Each round uses ~4 nodes; 8 rounds × 4 + overhead = ~40 steps needed
        result = await question_paper_graph.ainvoke(
            initial_state,
            config={"recursion_limit": 60},
        )

        final_paper = result.get("final_paper", {})
        answer_key = result.get("answer_key", [])
        coverage_gaps = result.get("coverage_gaps", [])
        covered_topics = result.get("covered_topics", [])
        question_count = final_paper.get("question_count", 0)

        # 4. Persist result by inlining JSON directly into SurrealQL.
        # SurrealDB 2.6.x Python driver silently drops nested dicts/lists when
        # passed as query parameters ($var) or via merge()/update() methods.
        # Inlining the JSON string directly into the query avoids the driver bug.
        import json as _json
        from open_notebook.database.repository import repo_query
        _fp_json = _json.dumps(final_paper)
        _ak_json = _json.dumps(answer_key)
        _cg_json = _json.dumps(coverage_gaps)
        _ct_json = _json.dumps(covered_topics)
        await repo_query(
            f"UPDATE {paper_id} MERGE "
            f"{{final_paper: {_fp_json}, answer_key: {_ak_json}, "
            f"coverage_gaps: {_cg_json}, covered_topics: {_ct_json}, status: 'completed'}}",
            {},
        )
        logger.info(f"Saved paper {paper_id}: {question_count} questions")

        processing_time = time.time() - start_time
        logger.info(
            f"Question paper {paper_id} completed: {question_count} questions "
            f"in {processing_time:.1f}s"
        )

        return GeneratePaperOutput(
            success=True,
            paper_id=paper_id,
            processing_time=processing_time,
            question_count=question_count,
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
