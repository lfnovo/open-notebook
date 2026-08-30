"""Offline tests for optional Bank Batch minimum-target mode + batch budgets."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.question_paper_service import (
    GenerateBankBatchRequest,
    QuestionPaperService,
    _history_display_status,
)
from open_notebook.graphs import question_bank_batch as qbb
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    BANK_BATCH_STOP_FULL_TARGET,
    BANK_BATCH_STOP_MIN_ATTEMPT_BUDGET,
    BANK_BATCH_STOP_MIN_TIME_BUDGET,
    BANK_BATCH_STOP_NORMAL_PARTIAL,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    audit_bank_batch,
    bank_batch_budget_exhausted,
    bank_batch_from_dict,
    bank_batch_generation_budget_block_reason,
    resolve_bank_batch_stop_reason,
    validate_minimum_accepted_questions,
    validate_optional_batch_budget,
)


def _bp(**overrides):
    base = {
        "book_id": "question_book:test",
        "grade": "9",
        "subject": "Financial Literacy",
        "chapter": 2,
        "difficulty": "easy",
        "total_questions": 15,
        "single_correct": 11,
        "multiple_correct": 4,
        "language": "en",
    }
    base.update(overrides)
    return bank_batch_from_dict(base)


def _passed(
    q_num: int,
    *,
    answer_type: str = "single_correct",
    text: str | None = None,
) -> dict:
    stems = [
        "What is the main purpose of a savings account for students?",
        "How does a fixed deposit differ from a current account?",
        "Which fee applies when a credit card payment is late?",
        "What happens when a debit card PIN is entered incorrectly thrice?",
        "Why should a monthly budget include emergency savings first?",
        "How is an annual interest rate usually expressed to customers?",
        "What does compound interest add that simple interest does not?",
        "When is simple interest typically calculated on a short loan?",
        "Which cost is paid regularly to keep an insurance policy active?",
        "What do mutual funds pool from many investors to buy?",
        "Why can share prices rise or fall on a stock exchange?",
        "What is the usual goal of a long-term pension contribution?",
        "Which document is needed before tax on salary is computed?",
        "What asset may a bank accept as security for a large loan?",
        "How is an EMI amount related to principal and tenure?",
        "Which feature helps identify a genuine currency note quickly?",
        "What must a user link before sending money from a digital wallet?",
        "How does UPI allow a transfer without sharing bank account numbers?",
        "What is written on a cheque to authorize a bank to pay someone?",
        "Why do banks ask for KYC documents when opening an account?",
    ]
    return {
        "question_number": q_num,
        "question": text or stems[(q_num - 1) % len(stems)],
        "type": "mcq" if answer_type == "single_correct" else "multi_correct",
        "answer_type": answer_type,
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0] if answer_type == "single_correct" else [0, 1],
        "answer": "A" if answer_type == "single_correct" else "A, B",
        "explanation": "Grounded in the chapter.",
        "topic": "Credit",
        "sub_topic": f"topic-{q_num}",
        "grade": "9",
        "subject": "Financial Literacy",
        "chapter": 2,
        "chapter_title": "Chapter 2",
        "target_difficulty": "easy",
        "validated_cognitive_difficulty": "easy",
        "difficulty_score": 10,
        "difficulty_scores": {},
        "validation_status": "passed",
        "validation_reasons": [],
        "generation_attempts": 1,
    }


def _approved_n(n: int, *, single: int | None = None) -> list:
    """Build n distinct passed questions; first `single` are single_correct."""
    if single is None:
        single = min(n, 11)
    out = []
    for i in range(1, n + 1):
        at = "single_correct" if i <= single else "multiple_correct"
        out.append(_passed(i, answer_type=at))
    return out


def _failed(nums: list[int]) -> list:
    return [
        {
            "question_number": i,
            "validation_status": "needs_manual_review",
            "validation_reasons": ["quality checks failed"],
            "target_difficulty": "easy",
            "answer_type": "single_correct",
            "chapter": 2,
        }
        for i in nums
    ]


class TestMinimumAcceptedValidation:
    def test_omitted_is_none(self):
        assert validate_minimum_accepted_questions(None, requested=15) is None

    def test_valid_range(self):
        assert validate_minimum_accepted_questions(10, requested=15) == 10
        assert validate_minimum_accepted_questions(1, requested=15) == 1
        assert validate_minimum_accepted_questions(15, requested=15) == 15

    def test_minimum_greater_than_requested_errors(self):
        with pytest.raises(ValueError, match="must be <= total_questions"):
            validate_minimum_accepted_questions(16, requested=15)

    def test_minimum_zero_or_negative_errors(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_minimum_accepted_questions(0, requested=15)
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_minimum_accepted_questions(-1, requested=15)

    def test_budget_fields_require_positive(self):
        assert validate_optional_batch_budget(None, field_name="x") is None
        assert validate_optional_batch_budget(50, field_name="x") == 50
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_optional_batch_budget(0, field_name="max_batch_generation_attempts")


class TestStopReasonClassification:
    def test_full_target_reached(self):
        assert (
            resolve_bank_batch_stop_reason(requested=15, accepted=15, failed_count=0)
            == BANK_BATCH_STOP_FULL_TARGET
        )

    def test_minimum_at_10_attempt_budget(self):
        reason = resolve_bank_batch_stop_reason(
            requested=15,
            accepted=10,
            failed_count=5,
            minimum_accepted=10,
            budget_exhausted_reason="attempt_budget",
        )
        assert reason == BANK_BATCH_STOP_MIN_ATTEMPT_BUDGET

    def test_minimum_at_12_time_budget(self):
        reason = resolve_bank_batch_stop_reason(
            requested=15,
            accepted=12,
            failed_count=3,
            minimum_accepted=10,
            budget_exhausted_reason="time_budget",
        )
        assert reason == BANK_BATCH_STOP_MIN_TIME_BUDGET

    def test_accepted_9_minimum_not_reached(self):
        reason = resolve_bank_batch_stop_reason(
            requested=15,
            accepted=9,
            failed_count=6,
            minimum_accepted=10,
            budget_exhausted_reason="attempt_budget",
        )
        assert reason == BANK_BATCH_STOP_NORMAL_PARTIAL
        assert reason != BANK_BATCH_STOP_MIN_ATTEMPT_BUDGET

    def test_minimum_omitted_partial_is_normal(self):
        reason = resolve_bank_batch_stop_reason(
            requested=15, accepted=10, failed_count=5, minimum_accepted=None
        )
        assert reason == BANK_BATCH_STOP_NORMAL_PARTIAL


class TestAuditMinimumTarget:
    def test_requested_15_minimum_10_accepted_15_full_success(self):
        bp = _bp(single_correct=11, multiple_correct=4)
        approved = _approved_n(15, single=11)
        audit = audit_bank_batch(
            bp,
            approved,
            [],
            minimum_accepted_questions=10,
            generated_attempts=40,
            runtime_seconds=12.5,
        )
        assert audit["status"] == "completed"
        assert audit["ok"] is True
        assert audit["accepted"] == 15
        assert audit["requested"] == 15
        assert audit["full_target_reached"] is True
        assert audit["minimum_target_reached"] is True
        assert audit["stop_reason"] == BANK_BATCH_STOP_FULL_TARGET
        assert audit["minimum_accepted_questions"] == 10
        assert audit["actual"]["single_correct"] == 11
        assert audit["actual"]["multiple_correct"] == 4

    def test_budget_at_10_partial_graceful_stop(self):
        bp = _bp()
        approved = _approved_n(10, single=8)
        failed = _failed(list(range(11, 16)))
        audit = audit_bank_batch(
            bp,
            approved,
            failed,
            minimum_accepted_questions=10,
            budget_exhausted_reason="attempt_budget",
            generated_attempts=55,
            runtime_seconds=90.0,
        )
        assert audit["status"] == "completed_partial"
        assert audit["accepted"] == 10
        assert audit["requested"] == 15
        assert audit["ok"] is False
        assert audit["full_target_reached"] is False
        assert audit["minimum_target_reached"] is True
        assert audit["stop_reason"] == BANK_BATCH_STOP_MIN_ATTEMPT_BUDGET
        diag = audit["target_diagnostics"]
        assert diag["remaining_slots"] == 5
        assert diag["accepted_single_correct"] == 8
        assert diag["accepted_multiple_correct"] == 2
        assert diag["total_generation_attempts"] == 55
        # Must not pretend requested mix was completed
        assert audit["expected"]["single_correct"] == 11
        assert audit["actual"]["single_correct"] == 8

    def test_budget_at_12_partial_with_12(self):
        bp = _bp()
        approved = _approved_n(12, single=9)
        failed = _failed([13, 14, 15])
        audit = audit_bank_batch(
            bp,
            approved,
            failed,
            minimum_accepted_questions=10,
            budget_exhausted_reason="attempt_budget",
        )
        assert audit["status"] == "completed_partial"
        assert audit["accepted"] == 12
        assert audit["minimum_target_reached"] is True
        assert audit["stop_reason"] == BANK_BATCH_STOP_MIN_ATTEMPT_BUDGET

    def test_accepted_9_not_minimum_success(self):
        bp = _bp()
        approved = _approved_n(9, single=7)
        failed = _failed(list(range(10, 16)))
        audit = audit_bank_batch(
            bp,
            approved,
            failed,
            minimum_accepted_questions=10,
            budget_exhausted_reason="attempt_budget",
        )
        assert audit["status"] == "completed_partial"
        assert audit["accepted"] == 9
        assert audit["minimum_target_reached"] is False
        assert audit["stop_reason"] == BANK_BATCH_STOP_NORMAL_PARTIAL

    def test_minimum_omitted_unchanged_semantics(self):
        bp = _bp()
        approved = _approved_n(10, single=8)
        failed = _failed(list(range(11, 16)))
        audit = audit_bank_batch(bp, approved, failed)
        assert audit["status"] == "completed_partial"
        assert audit["minimum_accepted_questions"] is None
        assert audit["minimum_target_reached"] is False
        assert audit["stop_reason"] == BANK_BATCH_STOP_NORMAL_PARTIAL


class TestBatchBudgetHelpers:
    def test_no_ceiling_does_not_block(self):
        state = {
            "bank_batch_mode": True,
            "cost_diagnostics": {"generated_attempts": 999},
        }
        assert bank_batch_generation_budget_block_reason(state) is None
        assert bank_batch_budget_exhausted(state) is False

    def test_attempt_ceiling_blocks(self):
        state = {
            "bank_batch_mode": True,
            "max_batch_generation_attempts": 10,
            "cost_diagnostics": {"generated_attempts": 10},
        }
        assert (
            bank_batch_generation_budget_block_reason(state) == "attempt_budget"
        )

    def test_time_ceiling_blocks(self):
        state = {
            "bank_batch_mode": True,
            "max_batch_runtime_seconds": 30,
            "batch_started_at": 1000.0,
        }
        assert (
            bank_batch_generation_budget_block_reason(state, now=1035.0)
            == "time_budget"
        )

    def test_sticky_exhausted_reason(self):
        state = {
            "bank_batch_mode": True,
            "batch_budget_exhausted_reason": "attempt_budget",
            "max_batch_generation_attempts": 1000,
            "cost_diagnostics": {"generated_attempts": 0},
        }
        assert (
            bank_batch_generation_budget_block_reason(state) == "attempt_budget"
        )


class TestOrchestrationGates:
    def test_needs_target_refill_skips_when_budget_exhausted(self):
        state = {
            "bank_batch_mode": True,
            "approved": _approved_n(10),
            "failed_slots": _failed([11, 12, 13, 14, 15]),
            "bank_batch_blueprint": {
                "book_id": "question_book:test",
                "grade": "9",
                "subject": "Financial Literacy",
                "chapter": 2,
                "difficulty": "easy",
                "total_questions": 15,
                "single_correct": 11,
                "multiple_correct": 4,
                "language": "en",
            },
            "target_refill_cycles_done": 0,
            "max_target_refill_cycles": 1,
            "batch_budget_exhausted_reason": "attempt_budget",
            "minimum_accepted_questions": 10,
        }
        assert qbb._needs_target_refill(state) == "audit_bank_batch"

    def test_needs_refill_skips_when_budget_exhausted(self):
        state = {
            "bank_batch_mode": True,
            "failed_slots": _failed([11]),
            "batch_budget_exhausted_reason": "time_budget",
        }
        assert qbb._needs_refill_bank(state) == "mark_after_normal_refill"

    def test_needs_target_refill_continues_when_min_met_but_budget_open(self):
        """Minimum alone must not stop; continue toward full requested count."""
        state = {
            "bank_batch_mode": True,
            "approved": _approved_n(10),
            "failed_slots": _failed([11, 12, 13, 14, 15]),
            "bank_batch_blueprint": {
                "book_id": "question_book:test",
                "grade": "9",
                "subject": "Financial Literacy",
                "chapter": 2,
                "difficulty": "easy",
                "total_questions": 15,
                "single_correct": 11,
                "multiple_correct": 4,
                "language": "en",
            },
            "target_refill_cycles_done": 0,
            "max_target_refill_cycles": 1,
            "minimum_accepted_questions": 10,
            # no batch budget exhausted
        }
        assert qbb._needs_target_refill(state) == "bank_target_refill"


class TestAcceptedUntouchedAndNoPromotion:
    @pytest.mark.asyncio
    async def test_budget_stop_does_not_regenerate_accepted(self):
        approved = _approved_n(10, single=8)
        snapshot = [dict(q) for q in approved]
        failed = _failed([11, 12, 13, 14, 15])
        state = {
            "bank_batch_mode": True,
            "approved": approved,
            "failed_slots": failed,
            "used_stems": [q["question"] for q in approved],
            "rejected_with_feedback": [],
            "chapter_chunks": {"2": ["chunk"]},
            "max_refill_attempts": 5,
            "slot_concurrency": 3,
            "max_batch_generation_attempts": 1,
            "cost_diagnostics": {"generated_attempts": 1},
            "batch_budget_exhausted_reason": "attempt_budget",
            "refill_diagnostics": {},
            "bank_intent_assignments": {},
            "bank_intent_remaining": [],
            "intent_diagnostics": {},
        }

        generate = AsyncMock(return_value=None)
        with patch.object(qp, "_generate_for_slot", generate):
            result = await qp.refill_slots(state)

        generate.assert_not_called()
        assert len(result["approved"]) == 10
        for a, b in zip(result["approved"], snapshot):
            assert a["question"] == b["question"]
            assert a["validation_status"] == "passed"
        assert len(result["failed_slots"]) == 5
        # Rejected/failed never promoted
        assert all(f.get("validation_status") != "passed" for f in result["failed_slots"])

    @pytest.mark.asyncio
    async def test_persist_only_passed_accepted(self):
        approved = _approved_n(10, single=8) + [
            {
                **_passed(99),
                "validation_status": "needs_manual_review",
            }
        ]
        state = {
            "approved": approved,
            "batch_id": "question_bank_batch:min",
            "book_id": "question_book:x",
            "chapter_chunks": {"2": ["c"]},
        }

        async def _save(data):
            class R:
                id = f"question_bank:{data['question'][:12]}"

            return R()

        with patch(
            "open_notebook.database.repository.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "open_notebook.graphs.question_bank_batch.QuestionRecord.save_one",
            new_callable=AsyncMock,
            side_effect=_save,
        ) as save:
            result = await qbb.persist_bank_batch(state)
        assert len(result["persisted_question_ids"]) == 10
        assert save.await_count == 10


class TestHistoryAndApiSurface:
    def test_history_remains_accepted_over_requested(self):
        assert _history_display_status("completed_partial", 10, 15) == "partial"
        assert _history_display_status("completed", 15, 15) == "completed"

    def test_request_model_accepts_optional_fields(self):
        req = GenerateBankBatchRequest(
            book_id="question_book:x",
            grade="9",
            subject="Financial Literacy",
            chapter=2,
            difficulty="easy",
            total_questions=15,
            single_correct=11,
            multiple_correct=4,
            minimum_accepted_questions=10,
            max_batch_generation_attempts=60,
            max_batch_runtime_seconds=900,
        )
        assert req.minimum_accepted_questions == 10
        assert req.max_batch_generation_attempts == 60

    def test_request_model_omitted_compatible(self):
        req = GenerateBankBatchRequest(
            book_id="question_book:x",
            grade="9",
            subject="Financial Literacy",
            chapter=2,
            difficulty="easy",
            total_questions=15,
            single_correct=11,
            multiple_correct=4,
        )
        assert req.minimum_accepted_questions is None
        assert req.max_batch_generation_attempts is None
        assert req.max_batch_runtime_seconds is None

    @pytest.mark.asyncio
    async def test_api_rejects_minimum_gt_requested(self):
        req = GenerateBankBatchRequest(
            book_id="question_book:x",
            grade="9",
            subject="Financial Literacy",
            chapter=2,
            difficulty="easy",
            total_questions=15,
            single_correct=11,
            multiple_correct=4,
            minimum_accepted_questions=20,
        )
        with pytest.raises(HTTPException) as ei:
            await QuestionPaperService.create_and_submit_bank_batch(req)
        assert ei.value.status_code == 400
        assert "minimum_accepted_questions" in str(ei.value.detail)

    @pytest.mark.asyncio
    async def test_api_rejects_minimum_le_zero(self):
        req = GenerateBankBatchRequest(
            book_id="question_book:x",
            grade="9",
            subject="Financial Literacy",
            chapter=2,
            difficulty="easy",
            total_questions=15,
            single_correct=11,
            multiple_correct=4,
            minimum_accepted_questions=0,
        )
        with pytest.raises(HTTPException) as ei:
            await QuestionPaperService.create_and_submit_bank_batch(req)
        assert ei.value.status_code == 400


class TestNonRegressionGuarantees:
    def test_attempt_limits_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_no_new_llm_call_in_minimum_helpers(self):
        src = inspect.getsource(resolve_bank_batch_stop_reason)
        src += inspect.getsource(bank_batch_generation_budget_block_reason)
        src += inspect.getsource(audit_bank_batch)
        assert "provision_langchain_model" not in src
        assert "ainvoke" not in src
        assert "openai" not in src.lower()

    def test_cognitive_thresholds_unchanged(self):
        from open_notebook.graphs.question_paper_blueprint import map_cognitive_score

        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"

    def test_final_paper_graph_unchanged(self):
        paper_src = inspect.getsource(qp.build_question_paper_graph)
        assert "minimum_accepted_questions" not in paper_src
        assert "max_batch_generation_attempts" not in paper_src
        assert "bank_target_refill" not in paper_src

    def test_concurrent_validators_and_intent_retirement_still_present(self):
        fill_src = inspect.getsource(qp.fill_slots)
        assert "asyncio.gather" in fill_src
        assert "apply_academic_failure_intent_policy" in fill_src
        assert "bank_batch_generation_budget_block_reason" in fill_src

    def test_step6_answer_position_still_in_audit_node(self):
        assert "apply_answer_position_audit" in inspect.getsource(
            qbb.audit_bank_batch_node
        )

    def test_length_recovery_constants_bank_batch_starts_at_4096(self):
        from open_notebook.graphs.question_paper_blueprint import (
            empty_bank_cost_diagnostics,
        )

        d = empty_bank_cost_diagnostics()
        assert d["length_limit_retry_initial_tokens"] == 4096
        assert d["length_limit_retry_retry_tokens"] == 4096
        assert qp.GENERATOR_MAX_TOKENS == 2048
        assert qp.GENERATOR_LENGTH_RETRY_MAX_TOKENS == 4096
        assert qp.BANK_BATCH_GENERATOR_MAX_TOKENS == 4096
