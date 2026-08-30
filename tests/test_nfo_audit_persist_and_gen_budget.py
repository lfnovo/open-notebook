"""Regression: audit persist crash + Bank Batch 4096-first generation.

Offline only. Does not change validators, thresholds, grounding, or Final Paper.
"""

from __future__ import annotations

import inspect
import time
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import question_bank_batch as qbb
from open_notebook.graphs import question_paper as qp


def _slot(**kwargs) -> qp.QuestionSlot:
    from open_notebook.graphs.question_paper_blueprint import QuestionSlot

    defaults = dict(
        question_number=1,
        chapter=1,
        chapter_title="Chapter 1",
        target_difficulty="easy",
        answer_type="single_correct",
        grade="9",
        subject="Financial Literacy",
    )
    defaults.update(kwargs)
    return QuestionSlot(**defaults)


def _ok_payload():
    return {
        "question": "What is a household budget?",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "A budget plans income and spending.",
    }


def _approved(n: int = 1) -> dict:
    return {
        "question_number": n,
        "question": f"Unique accepted stem {n} about a taught budget concept?",
        "type": "mcq",
        "answer_type": "single_correct",
        "options": ["Cash", "Credit", "Barter", "Loan", "Tax"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "Cash is taught as a medium of exchange.",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "grade": "9",
        "subject": "Financial Literacy",
        "chapter": 3,
        "chapter_title": "Chapter 3",
        "target_difficulty": "medium",
        "validated_cognitive_difficulty": "medium",
        "difficulty_score": 14,
        "difficulty_scores": {},
        "validation_status": "passed",
        "validation_reasons": [],
        "generation_attempts": 1,
    }


def _blueprint() -> dict:
    return {
        "book_id": "question_book:o0chwk6eqt9rjcwmluas",
        "grade": "9",
        "subject": "Financial Literacy",
        "chapter": 3,
        "difficulty": "medium",
        "total_questions": 2,
        "single_correct": 2,
        "multiple_correct": 0,
        "language": "en",
    }


def _length_err() -> ExternalServiceError:
    err = ExternalServiceError(
        "AI service error: Could not parse response content as the length "
        "limit was reached - CompletionUsage(reasoning_tokens=2048)"
    )
    err.__cause__ = type("LengthFinishReasonError", (Exception,), {})(
        "length limit was reached"
    )
    return err


class TestAuditNodePersistCrashFix:
    def test_runtime_s_assigned_before_finalize(self):
        src = inspect.getsource(qbb.audit_bank_batch_node)
        assign = src.find("runtime_s =")
        use = src.find("processing_time_seconds=runtime_s")
        assert assign != -1
        assert use != -1
        assert assign < use

    def test_graph_still_audits_then_persists(self):
        src = inspect.getsource(qbb.build_question_bank_batch_graph)
        assert 'graph.add_edge("audit_bank_batch", "persist_bank_batch")' in src
        paper_src = inspect.getsource(qp.build_question_paper_graph)
        assert "persist_bank_batch" not in paper_src
        assert "audit_bank_batch" not in paper_src

    @pytest.mark.asyncio
    async def test_audit_node_does_not_crash_and_keeps_accepted(self):
        approved = [_approved(1), _approved(2)]
        state = {
            "bank_batch_blueprint": _blueprint(),
            "approved": approved,
            "failed_slots": [],
            "rejected_with_feedback": [],
            "cost_diagnostics": {"generated_attempts": 6, "core_generation_llm_calls": 6},
            "intent_diagnostics": {},
            "refill_diagnostics": {},
            "bank_duplicate_seed_questions": [],
            "batch_started_at": time.time() - 12.5,
            "minimum_accepted_questions": None,
        }
        out = await qbb.audit_bank_batch_node(state)
        assert len(out["approved"]) == 2
        assert out["audit"]["accepted"] == 2
        cost = out["cost_diagnostics"]
        assert cost is not None
        assert "llm_usage_totals" in cost
        assert "stage_usage_table" in cost
        assert out["audit"]["cost_diagnostics"] is cost

    @pytest.mark.asyncio
    async def test_audit_then_persist_saves_passed_questions(self):
        approved = [_approved(1), _approved(2)]
        audit_state = {
            "bank_batch_blueprint": _blueprint(),
            "approved": approved,
            "failed_slots": [],
            "rejected_with_feedback": [],
            "cost_diagnostics": {"generated_attempts": 4},
            "intent_diagnostics": {},
            "refill_diagnostics": {},
            "bank_duplicate_seed_questions": [],
            "batch_started_at": time.time() - 5.0,
        }
        audited = await qbb.audit_bank_batch_node(audit_state)

        persist_state = {
            "approved": audited["approved"],
            "batch_id": "question_bank_batch:auditfix",
            "book_id": "question_book:o0chwk6eqt9rjcwmluas",
            "chapter_chunks": {"3": ["chunk"]},
        }

        saved = []

        async def _save_one(data):
            saved.append(data)
            class R:
                id = f"question_bank:{len(saved)}"

            return R()

        with patch(
            "open_notebook.database.repository.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "open_notebook.graphs.question_bank_batch.QuestionRecord.save_one",
            new_callable=AsyncMock,
            side_effect=_save_one,
        ):
            persisted = await qbb.persist_bank_batch(persist_state)
        assert len(persisted["persisted_question_ids"]) == 2
        assert len(saved) == 2


class TestBankBatchGeneratorBudget:
    @pytest.mark.asyncio
    async def test_bank_batch_uses_4096_once_no_2048_probe(self):
        class R:
            def model_dump(self):
                payload = _ok_payload()
                payload["explanation"] = "should be stripped"
                return payload

        mock_invoke = AsyncMock(return_value=R())
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False, "generator_model": None, "bank_batch_mode": True},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is not None
        assert out.get("explanation") == ""
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 4096
        assert int(cost.get("length_limit_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_bank_batch_length_error_does_not_retry_same_budget(self):
        mock_invoke = AsyncMock(side_effect=_length_err())
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False, "bank_batch_mode": True},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is None
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 4096
        assert int(cost.get("length_limit_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_final_paper_still_2048_then_4096_on_length_error(self):
        class R:
            def model_dump(self):
                return _ok_payload()

        mock_invoke = AsyncMock(side_effect=[_length_err(), R()])
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False, "generator_model": None},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is not None
        assert mock_invoke.await_count == 2
        assert mock_invoke.await_args_list[0].kwargs.get("max_tokens") == 2048
        assert mock_invoke.await_args_list[1].kwargs.get("max_tokens") == 4096
        assert cost["length_limit_retry_attempted"] == 1
        assert cost["length_limit_retry_succeeded"] == 1

    def test_constants_and_validators_untouched(self):
        assert qp.GENERATOR_MAX_TOKENS == 2048
        assert qp.BANK_BATCH_GENERATOR_MAX_TOKENS == 4096
        fill_src = inspect.getsource(qp.fill_slots)
        assert "asyncio.gather" in fill_src
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "BANK_BATCH_GENERATOR_MAX_TOKENS" in gen_src
        assert "allow_length_retry" in gen_src
        from open_notebook.graphs.question_paper_blueprint import map_cognitive_score

        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(19) == "difficult"
