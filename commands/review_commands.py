"""Async command for the repo-review feature.

Runs the (potentially many-minutes, many-LLM-call) review_graph in the background:
distill guidance from the user's sources, scan the local repo, synthesize a report,
then persist the report as an AI Note and update the Review record.
"""

import time
from collections import Counter
from typing import Optional

from loguru import logger
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.domain.notebook import Note
from open_notebook.domain.review import Review
from open_notebook.exceptions import ConfigurationError, InvalidInputError
from open_notebook.utils.repo_scan import validate_repo_path

try:
    from open_notebook.graphs.repo_review import graph as review_graph
except ImportError as e:
    logger.error(f"Failed to import repo_review graph: {e}")
    raise ValueError("repo_review graph not available")

VERDICTS = ["follows", "partial", "violates", "not-found"]


class RepoReviewInput(CommandInput):
    review_id: str
    theme: str
    repo_path: str
    notebook_id: Optional[str] = None
    strategy_model: Optional[str] = None
    answer_model: Optional[str] = None
    final_answer_model: Optional[str] = None


class RepoReviewOutput(CommandOutput):
    success: bool
    review_id: str
    report_note_id: Optional[str] = None
    principles_checked: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None


@command(
    "repo_review",
    app="open_notebook",
    retry={
        "max_attempts": 3,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        # Permanent failures: bad path / unconfigured feature / validation. Don't retry.
        "stop_on": [ValueError, ConfigurationError, InvalidInputError],
        "retry_log_level": "debug",
    },
)
async def repo_review_command(input_data: RepoReviewInput) -> RepoReviewOutput:
    start_time = time.time()
    review: Optional[Review] = None
    try:
        logger.info(
            f"Starting repo review {input_data.review_id} on {input_data.repo_path} "
            f"(theme: {input_data.theme!r})"
        )

        review = await Review.get(input_data.review_id)
        if not review:
            raise ValueError(f"Review '{input_data.review_id}' not found")

        # Defense in depth: re-validate the path inside the worker. Raises on escape.
        resolved = validate_repo_path(input_data.repo_path)

        review.status = "running"
        review.command_id = (
            str(input_data.execution_context.command_id)
            if input_data.execution_context
            else None
        )
        await review.save()

        config = {
            "configurable": {
                "strategy_model": input_data.strategy_model,
                "answer_model": input_data.answer_model,
                "final_answer_model": input_data.final_answer_model,
            }
        }
        result = await review_graph.ainvoke(
            {  # type: ignore[arg-type]
                "theme": input_data.theme,
                "repo_path": str(resolved),
                "notebook_id": input_data.notebook_id or "",
            },
            config=config,
        )

        findings = result.get("findings", []) or []
        report = result.get("report", "") or "No report was generated."

        # Summarize verdict counts for the Review record / UI badges.
        counts = Counter(f.get("verdict", "not-found") for f in findings)
        summary = {v: counts.get(v, 0) for v in VERDICTS}

        # Persist the report as an AI Note linked to the notebook.
        note = Note(
            title=f"Repo Review: {input_data.theme}"[:120],
            content=report,
            note_type="ai",
        )
        await note.save()
        if input_data.notebook_id:
            await note.add_to_notebook(input_data.notebook_id)

        review.status = "completed"
        review.report_note_id = str(note.id) if note.id else None
        review.summary = summary
        await review.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Completed repo review {input_data.review_id}: "
            f"{len(findings)} principles in {processing_time:.1f}s ({summary})"
        )
        return RepoReviewOutput(
            success=True,
            review_id=input_data.review_id,
            report_note_id=review.report_note_id,
            principles_checked=len(findings),
            processing_time=processing_time,
        )

    except (ValueError, ConfigurationError, InvalidInputError) as e:
        # Permanent failure — record it and re-raise so the job is marked `failed`.
        logger.error(f"Repo review {input_data.review_id} failed (permanent): {e}")
        if review is not None:
            try:
                review.status = "failed"
                review.error_message = str(e)
                await review.save()
            except Exception as save_err:
                logger.error(f"Failed to record review failure: {save_err}")
        raise
    except Exception as e:
        # Transient failure — will be retried. Mark failed only on the last attempt
        # is not easily known here, so leave status as 'running' and let retry handle it.
        logger.debug(f"Transient error in repo review {input_data.review_id}: {e}")
        raise
