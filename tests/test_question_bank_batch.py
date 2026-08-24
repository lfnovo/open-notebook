"""Tests for Question Bank Batch (Phase 1) — schema, slots, audit, persistence hooks."""

import inspect
import json
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    BANK_BATCH_DUPLICATE_RETRY_CORE,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    audit_bank_batch,
    bank_batch_from_dict,
    bank_target_refill_cycles,
    build_bank_batch_slots,
    build_rejected_attempt_record,
    build_slot_avoidance_history,
    classify_bank_refill_strategy,
    compute_bank_batch_saturation_diagnostics,
    evaluate_answer_type,
    find_lexical_duplicate_match,
    format_bank_batch_duplicate_retry_guidance,
    format_bank_batch_strategy_guidance,
    format_underused_concept_hints,
    generator_structural_self_check,
    is_bank_diversity_planner_enabled,
    is_near_duplicate,
    select_chunk_avoiding_history,
)
from open_notebook.graphs.question_bank_batch import (
    _bank_record_from_approved,
    persist_bank_batch,
)


def _blueprint_dict(**overrides):
    base = {
        "book_id": "question_book:test",
        "grade": "5",
        "subject": "Financial Literacy",
        "chapter": 1,
        "difficulty": "easy",
        "total_questions": 50,
        "single_correct": 40,
        "multiple_correct": 10,
        "language": "en",
    }
    base.update(overrides)
    return base


def _passed_question(
    *,
    q_num: int,
    answer_type: str = "single_correct",
    text: str | None = None,
    chapter: int = 1,
    grade: str = "5",
    difficulty: str = "easy",
) -> dict:
    return {
        "question_number": q_num,
        "question": text or f"Unique bank question {q_num} about saving money?",
        "type": "mcq" if answer_type == "single_correct" else "multi_correct",
        "answer_type": answer_type,
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0] if answer_type == "single_correct" else [0, 1],
        "answer": "A" if answer_type == "single_correct" else "A, B",
        "explanation": "Because the chapter explains this concept clearly.",
        "topic": "Saving",
        "sub_topic": "Piggy banks",
        "grade": grade,
        "subject": "Financial Literacy",
        "chapter": chapter,
        "chapter_title": "Chapter 1",
        "target_difficulty": difficulty,
        "validated_cognitive_difficulty": difficulty,
        "difficulty_score": 10,
        "difficulty_scores": {},
        "validation_status": "passed",
        "validation_reasons": [],
        "generation_attempts": 1,
    }


class TestBankBatchBlueprintValidation:
    def test_chapter_easy_50_is_valid(self):
        bp = bank_batch_from_dict(_blueprint_dict())
        assert bp.total_questions == 50
        assert bp.single_correct == 40
        assert bp.multiple_correct == 10
        assert bp.difficulty == "easy"
        assert bp.chapter == 1

    def test_single_plus_multiple_must_equal_total(self):
        with pytest.raises(ValueError, match="must equal total_questions"):
            bank_batch_from_dict(_blueprint_dict(single_correct=30, multiple_correct=10))

    def test_requires_book_grade_subject(self):
        with pytest.raises(ValueError, match="book_id"):
            bank_batch_from_dict(_blueprint_dict(book_id=""))
        with pytest.raises(ValueError, match="grade"):
            bank_batch_from_dict(_blueprint_dict(grade=""))
        with pytest.raises(ValueError, match="subject"):
            bank_batch_from_dict(_blueprint_dict(subject=""))


class TestBuildBankBatchSlots:
    def test_only_requested_chapter_and_difficulty(self):
        bp = bank_batch_from_dict(
            _blueprint_dict(total_questions=5, single_correct=4, multiple_correct=1)
        )
        slots = build_bank_batch_slots(bp, chapter_title="Needs and Wants")
        assert len(slots) == 5
        assert all(s.chapter == 1 for s in slots)
        assert all(s.target_difficulty == "easy" for s in slots)
        assert sum(1 for s in slots if s.answer_type == "single_correct") == 4
        assert sum(1 for s in slots if s.answer_type == "multiple_correct") == 1

    def test_easy_only_no_medium_or_difficult_slots(self):
        bp = bank_batch_from_dict(
            _blueprint_dict(total_questions=12, single_correct=10, multiple_correct=2)
        )
        slots = build_bank_batch_slots(bp, chapter_title="Ch1")
        difficulties = {s.target_difficulty for s in slots}
        assert difficulties == {"easy"}


class TestAuditBankBatch:
    def test_50_of_50_completed(self):
        bp = bank_batch_from_dict(
            _blueprint_dict(total_questions=3, single_correct=2, multiple_correct=1)
        )
        approved = [
            _passed_question(q_num=1, answer_type="single_correct", text="Q1 about coins?"),
            _passed_question(q_num=2, answer_type="single_correct", text="Q2 about notes?"),
            _passed_question(q_num=3, answer_type="multiple_correct", text="Q3 about budgets?"),
        ]
        audit = audit_bank_batch(bp, approved, [])
        assert audit["status"] == "completed"
        assert audit["ok"] is True
        assert audit["accepted"] == 3
        assert audit["requested"] == 3

    def test_43_of_50_completed_partial(self):
        bp = bank_batch_from_dict(_blueprint_dict())
        approved = [
            _passed_question(
                q_num=i,
                answer_type="single_correct" if i <= 40 else "multiple_correct",
                text=f"Distinct partial batch question number {i}?",
            )
            for i in range(1, 44)
        ]
        failed = [
            {
                "question_number": i,
                "validation_status": "needs_manual_review",
                "validation_reasons": ["distractor quality failed"],
            }
            for i in range(44, 51)
        ]
        audit = audit_bank_batch(bp, approved, failed)
        assert audit["status"] == "completed_partial"
        assert audit["accepted"] == 43
        assert audit["requested"] == 50
        assert audit["failed"] == 7
        assert audit["failure_summary"]["failed_slot_count"] == 7

    def test_wrong_chapter_fails_audit(self):
        bp = bank_batch_from_dict(
            _blueprint_dict(total_questions=1, single_correct=1, multiple_correct=0)
        )
        approved = [_passed_question(q_num=1, chapter=2, text="Wrong chapter question?")]
        audit = audit_bank_batch(bp, approved, [])
        assert audit["ok"] is False
        assert any("chapter mismatch" in e for e in audit["errors"])

    def test_duplicate_within_batch_fails_audit(self):
        bp = bank_batch_from_dict(
            _blueprint_dict(total_questions=2, single_correct=2, multiple_correct=0)
        )
        text = "What is a savings account for children?"
        approved = [
            _passed_question(q_num=1, text=text),
            _passed_question(q_num=2, text=text),
        ]
        audit = audit_bank_batch(bp, approved, [])
        assert audit["ok"] is False
        assert any("duplicate" in e.lower() for e in audit["errors"])


class TestDuplicateContext:
    def test_seed_texts_included_in_duplicate_context(self):
        approved = [_passed_question(q_num=1, text="New question about loans?")]
        state = {
            "bank_duplicate_seed_texts": ["Existing bank question about loans?"],
            "bank_duplicate_seed_questions": [
                {
                    "chapter": 1,
                    "topic": "Loans",
                    "question": "Existing bank question about loans?",
                }
            ],
        }
        texts, qs = qp._duplicate_context(state, approved)
        assert len(texts) == 2
        assert len(qs) == 2

    @pytest.mark.asyncio
    async def test_bank_batch_mode_skips_global_bank_duplicate(self):
        with patch.object(qp, "check_bank_duplicate", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            assert await qp._is_external_duplicate("any text", {"bank_batch_mode": True}) is False
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_paper_mode_uses_global_bank_duplicate(self):
        with patch.object(qp, "check_bank_duplicate", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            assert await qp._is_external_duplicate("any text", {}) is True
            mock_check.assert_called_once()


class TestPersistBankBatch:
    @pytest.mark.asyncio
    async def test_passed_questions_persist_on_partial_batch(self):
        approved = [
            _passed_question(q_num=1, text="Persist me one?"),
            _passed_question(q_num=2, text="Persist me two?"),
            {
                **_passed_question(q_num=3, text="Reject me"),
                "validation_status": "rejected",
            },
        ]
        state = {
            "approved": approved,
            "batch_id": "question_bank_batch:abc",
            "book_id": "question_book:xyz",
            "chapter_chunks": {"1": ["chunk text"]},
        }

        async def _save(data):
            class R:
                id = f"question_bank:{len(data['question'])}"

            return R()

        with patch(
            "open_notebook.database.repository.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "open_notebook.graphs.question_bank_batch.QuestionRecord.save_one",
            new_callable=AsyncMock,
            side_effect=_save,
        ):
            result = await persist_bank_batch(state)
        assert len(result["persisted_question_ids"]) == 2

    @pytest.mark.asyncio
    async def test_failed_questions_not_persisted(self):
        approved = [
            {
                **_passed_question(q_num=1, text="Failed slot"),
                "validation_status": "needs_manual_review",
            }
        ]
        state = {
            "approved": approved,
            "batch_id": "question_bank_batch:abc",
            "book_id": "question_book:xyz",
            "chapter_chunks": {},
        }
        with patch(
            "open_notebook.database.repository.repo_query",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "open_notebook.graphs.question_bank_batch.QuestionRecord.save_one",
            new_callable=AsyncMock,
        ) as save_one:
            result = await persist_bank_batch(state)
        save_one.assert_not_called()
        assert result["persisted_question_ids"] == []

    @pytest.mark.asyncio
    async def test_retry_avoids_duplicate_persistence(self):
        approved = [_passed_question(q_num=1, text="Already saved question?")]
        state = {
            "approved": approved,
            "batch_id": "question_bank_batch:abc",
            "book_id": "question_book:xyz",
            "chapter_chunks": {},
        }
        with patch(
            "open_notebook.database.repository.repo_query",
            new_callable=AsyncMock,
            return_value=[{"id": "question_bank:existing", "question": "Already saved question?"}],
        ), patch(
            "open_notebook.graphs.question_bank_batch.QuestionRecord.save_one",
            new_callable=AsyncMock,
        ) as save_one:
            result = await persist_bank_batch(state)
        save_one.assert_not_called()
        assert result["persisted_question_ids"] == ["question_bank:existing"]


class TestBankRecordMapping:
    def test_bank_record_includes_batch_metadata(self):
        q = _passed_question(q_num=3, text="Metadata test?")
        record = _bank_record_from_approved(
            q,
            batch_id="question_bank_batch:batch1",
            book_id="question_book:book1",
            chapter_chunks={"1": ["a", "b", "c"]},
        )
        assert record["batch_id"] == "question_bank_batch:batch1"
        assert record["book_id"] == "question_book:book1"
        assert record["source_chunk_index"] is not None
        assert record["validation_status"] == "passed"


class TestBoundedRetries:
    def test_slot_and_refill_attempt_limits_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5


class TestBankBatchDiversityPlannerStep2:
    """Step 2: lightweight diversity planning — Bank Batch only."""

    def test_planner_preserves_difficulty_and_answer_type(self):
        from open_notebook.graphs.question_paper_blueprint import plan_bank_batch_diversity

        slot = QuestionSlot(
            question_number=3,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="multiple_correct",
            grade="5",
            subject="Financial Literacy",
        )
        plan = plan_bank_batch_diversity(
            slot=slot,
            attempt=1,
            catalog={"learning_outcomes": ["Understand money"], "sections": ["Barter"]},
            usage={"topic_counts": {"Barter": 3}, "intent_summaries": ["why barter failed"]},
            chunks=["chunk-a", "chunk-b"],
        )
        assert plan.target_difficulty == "easy"
        assert plan.answer_type == "multiple_correct"

    def test_heavily_used_intent_appears_in_avoid_guidance(self):
        from open_notebook.graphs.question_paper_blueprint import (
            format_diversity_guidance,
            plan_bank_batch_diversity,
            summarize_diversity_usage,
        )

        usage = summarize_diversity_usage(
            [
                {
                    "topic": "Barter System",
                    "sub_topic": "Disadvantages",
                    "question": "Why was barter difficult for two people to trade goods?",
                },
                {
                    "topic": "Barter System",
                    "sub_topic": "Disadvantages",
                    "question": "What made the barter system hard when exchanging goods?",
                },
            ]
        )
        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        plan = plan_bank_batch_diversity(
            slot=slot,
            attempt=1,
            catalog={
                "learning_outcomes": ["Describe functions of money"],
                "sections": ["Functions of Money", "Barter System"],
            },
            usage=usage,
            chunks=["a", "b", "c"],
        )
        assert "Barter System" in plan.avoid_topics
        guidance = format_diversity_guidance(plan)
        assert "Avoid repeating" in guidance
        assert "Barter" in guidance or "barter" in guidance.lower()

    def test_underused_section_can_be_preferred(self):
        from open_notebook.graphs.question_paper_blueprint import plan_bank_batch_diversity

        slot = QuestionSlot(
            question_number=2,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        plan = plan_bank_batch_diversity(
            slot=slot,
            attempt=1,
            catalog={
                "learning_outcomes": [],
                "sections": ["Barter System", "Unit of Account"],
            },
            usage={
                "topic_counts": {"Barter System": 5},
                "sub_topic_counts": {},
                "intent_summaries": ["why barter was difficult"],
                "intent_fingerprints": [],
                "used_chunk_indices": [0, 0, 0],
            },
            chunks=["c0", "c1", "c2"],
        )
        # Prefer should lean away from heavily used Barter
        assert "Unit of Account" in (plan.prefer_section or plan.prefer_topic)

    def test_retry_avoids_previous_chunk_when_alternatives_exist(self):
        from open_notebook.graphs.question_paper_blueprint import plan_bank_batch_diversity

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        plan = plan_bank_batch_diversity(
            slot=slot,
            attempt=2,
            catalog={"learning_outcomes": [], "sections": ["Money"]},
            usage={"topic_counts": {}, "used_chunk_indices": [0]},
            chunks=["chunk0", "chunk1", "chunk2"],
            previous_intent_words={"barter", "trade", "difficult"},
            previous_chunk_index=0,
        )
        assert plan.preferred_chunk_index != 0

    def test_bank_and_batch_questions_contribute_to_usage(self):
        from open_notebook.graphs.question_paper_blueprint import summarize_diversity_usage

        usage = summarize_diversity_usage(
            [
                {"topic": "Bank Topic", "sub_topic": "A", "question": "Existing bank question about savings?"},
                {"topic": "Batch Topic", "sub_topic": "B", "question": "Accepted batch question about coins?"},
            ]
        )
        assert usage["topic_counts"]["Bank Topic"] == 1
        assert usage["topic_counts"]["Batch Topic"] == 1
        assert len(usage["intent_summaries"]) == 2

    def test_diversity_guidance_only_in_bank_batch_generate(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        fill_src = inspect.getsource(qp.fill_slots)
        assert "diversity_guidance" in gen_src
        assert "bank_batch_mode" in fill_src
        assert "plan_bank_batch_diversity" in fill_src
        # Final Paper prepare must not set diversity catalog
        prep_src = inspect.getsource(qp.prepare_blueprint)
        assert "bank_diversity_catalog" not in prep_src

    @pytest.mark.asyncio
    async def test_final_paper_generate_has_no_diversity_block(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is X?",
                        "topic": "Money",
                        "sub_topic": "Coins",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": False, "language": "en"},
                "chapter text",
                None,
                diversity_guidance="DIVERSITY GUIDANCE should not appear unless bank batch",
            )
        # Explicit guidance arg ignored when not bank_batch_mode
        assert "DIVERSITY GUIDANCE" not in captured["user"]

    @pytest.mark.asyncio
    async def test_bank_batch_generate_includes_diversity_block(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is X?",
                        "topic": "Money",
                        "sub_topic": "Coins",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": True, "book_grounded": True, "language": "en"},
                "chapter text",
                None,
                diversity_guidance="\nDIVERSITY GUIDANCE (Bank Batch — soft preferences; still obey all quality rules):\n- Prefer: Unit of Account\n",
            )
        assert "DIVERSITY GUIDANCE" in captured["user"]
        assert "Unit of Account" in captured["user"]


class TestBankBatchTopicPromptStep1:
    """Step 1: Bank Batch prompt distinguishes Subject vs Topic; Final Paper unchanged."""

    def test_topic_equal_subject_still_rejected(self):
        from open_notebook.graphs.question_paper_blueprint import validate_topic_metadata

        errors = validate_topic_metadata(
            "Financial Literacy",
            "Barter System",
            "Chapter 1",
            subject="Financial Literacy",
        )
        assert any("must not equal subject" in e for e in errors)

    def test_generic_grade_and_chapter_still_invalid(self):
        from open_notebook.graphs.question_paper_blueprint import validate_topic_metadata

        assert any(
            "generic" in e.lower()
            for e in validate_topic_metadata("Grade 5", "", "Chapter 1", subject="Financial Literacy")
        )
        assert any(
            "chapter title" in e.lower() or "generic" in e.lower()
            for e in validate_topic_metadata("Chapter 1", "", "Chapter 1", subject="Financial Literacy")
        )

    def test_bank_batch_prompt_constant_requires_topic_differs_from_subject(self):
        rules = qp.BANK_BATCH_TOPIC_METADATA_RULES
        assert "must NOT equal Subject" in rules or "must not equal Subject" in rules.lower()
        assert "sub_topic" in rules.lower()
        assert "Financial Literacy" in rules  # illustrative examples only
        assert "Grade 5" in rules
        assert "Chapter 1" in rules

    def test_bank_batch_mode_injects_topic_rules_into_generation(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "bank_batch_mode" in gen_src
        assert "BANK_BATCH_TOPIC_METADATA_RULES" in gen_src
        assert "topic must NOT equal Subject" in gen_src or "must NOT equal Subject" in gen_src

    def test_final_paper_generator_system_unchanged_by_bank_batch_rules(self):
        # Shared system prompt must not include Bank Batch-only metadata rules.
        assert "BANK BATCH TOPIC" not in qp.GENERATOR_SYSTEM
        assert "must NOT equal Subject" not in qp.GENERATOR_SYSTEM

    @pytest.mark.asyncio
    async def test_final_paper_mode_does_not_append_bank_batch_topic_rules(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is a medium of exchange?",
                        "topic": "Money",
                        "sub_topic": "Functions",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because money buys goods.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": False, "topic": "Financial Literacy", "language": "en"},
                "chapter text about money",
                None,
            )
        assert "BANK BATCH TOPIC" not in captured["system"]
        assert "must NOT equal Subject" not in captured["user"]

    @pytest.mark.asyncio
    async def test_bank_batch_mode_appends_topic_rules(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is a medium of exchange?",
                        "topic": "Money",
                        "sub_topic": "Functions",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because money buys goods.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                    "topic": "Financial Literacy",
                    "language": "en",
                },
                "chapter text about money and barter",
                None,
            )
        assert "BANK BATCH TOPIC" in captured["system"]
        assert "must NOT equal Subject" in captured["system"]
        assert "must NOT equal Subject" in captured["user"]
        assert "sub_topic" in captured["user"].lower()


class TestBankDiversityPlannerFlagDefaultOff:
    """Step 2 planner remains available but default OFF (Step 1 path)."""

    def test_diversity_planner_flag_defaults_off(self, monkeypatch):
        monkeypatch.delenv("QUESTION_BANK_DIVERSITY_PLANNER", raising=False)
        assert is_bank_diversity_planner_enabled() is False

    def test_diversity_planner_flag_can_be_enabled(self, monkeypatch):
        monkeypatch.setenv("QUESTION_BANK_DIVERSITY_PLANNER", "true")
        assert is_bank_diversity_planner_enabled() is True
        monkeypatch.setenv("QUESTION_BANK_DIVERSITY_PLANNER", "0")
        assert is_bank_diversity_planner_enabled() is False

    def test_fill_slots_gates_planner_behind_flag(self):
        fill_src = inspect.getsource(qp.fill_slots)
        refill_src = inspect.getsource(qp.refill_slots)
        assert "is_bank_diversity_planner_enabled()" in fill_src
        assert "is_bank_diversity_planner_enabled()" in refill_src
        assert "plan_bank_batch_diversity" in fill_src  # code retained

    def test_final_paper_unchanged_by_diversity_flag(self):
        prep_src = inspect.getsource(qp.prepare_blueprint)
        assert "bank_diversity_catalog" not in prep_src
        assert "QUESTION_BANK_DIVERSITY_PLANNER" not in qp.GENERATOR_SYSTEM


class TestBankBatchMisconceptionDistractors:
    """Bank Batch misconception-based distractors + cheap generator self-check."""

    def test_distractor_prompt_asks_for_misconception_based_options(self):
        rules = qp.BANK_BATCH_DISTRACTOR_RULES
        assert "misconception" in rules.lower()
        assert "Concept" in rules or "concept" in rules
        assert "joke" in rules.lower() or "absurd" in rules.lower()
        assert "BANK BATCH DISTRACTOR" in rules

    def test_bank_batch_injects_distractor_rules_final_paper_does_not(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "BANK_BATCH_DISTRACTOR_RULES" in gen_src
        assert "BANK BATCH DISTRACTOR" not in qp.GENERATOR_SYSTEM

    @pytest.mark.asyncio
    async def test_bank_batch_mode_appends_distractor_rules(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is a medium of exchange?",
                        "topic": "Money",
                        "sub_topic": "Functions",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because money buys goods.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                    "language": "en",
                },
                "chapter text",
                None,
            )
        assert "BANK BATCH DISTRACTOR" in captured["system"]
        assert "misconception" in captured["system"].lower()
        assert "misconception" in captured["user"].lower()

    @pytest.mark.asyncio
    async def test_final_paper_mode_does_not_append_distractor_rules(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is X?",
                        "topic": "Money",
                        "sub_topic": "Coins",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": False, "language": "en"},
                "chapter text",
                None,
            )
        assert "BANK BATCH DISTRACTOR" not in captured["system"]
        assert "misconception" not in captured["user"].lower()

    def test_generator_structural_self_check_ok(self):
        errs = generator_structural_self_check(
            {
                "options": ["A", "B", "C", "D", "E"],
                "correct_indices": [0],
            },
            answer_type="single_correct",
        )
        assert errs == []

    def test_generator_structural_self_check_rejects_joke_and_bad_answer_set(self):
        errs = generator_structural_self_check(
            {
                "options": ["Correct", "Aliens did it", "C", "C", "E"],
                "correct_indices": [0, 1],
            },
            answer_type="single_correct",
        )
        assert any("joke" in e.lower() or "filler" in e.lower() for e in errs)
        assert any("distinct" in e.lower() for e in errs)
        assert any("exactly one" in e.lower() for e in errs)

    def test_generator_structural_self_check_multiple_requires_two(self):
        errs = generator_structural_self_check(
            {
                "options": ["A", "B", "C", "D", "E"],
                "correct_indices": [0],
            },
            answer_type="multiple_correct",
        )
        assert any("at least two" in e.lower() for e in errs)

    def test_fill_slots_runs_self_check_in_bank_batch(self):
        fill_src = inspect.getsource(qp.fill_slots)
        assert "generator_structural_self_check" in fill_src

    def test_answer_set_validation_unchanged(self):
        assert evaluate_answer_type("single_correct", [0], 5) == []
        assert any(
            "exactly one" in e.lower()
            for e in evaluate_answer_type("single_correct", [0, 1], 5)
        )
        assert evaluate_answer_type("multiple_correct", [0, 2], 5) == []
        assert any(
            "more than one" in e.lower()
            for e in evaluate_answer_type("multiple_correct", [1], 5)
        )


class TestBankBatchStep3ARejectedMetadataAndRetry:
    """Step 3A: rejected-attempt metadata, duplicate retry intent guidance, soft hints."""

    def test_rejected_stem_metadata_is_persisted(self):
        slot = QuestionSlot(
            question_number=3,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        rec = build_rejected_attempt_record(
            slot=slot,
            attempt=2,
            generated={
                "question": "What is currency?",
                "topic": "Currency",
                "sub_topic": "Definition",
            },
            rejection_reasons=["duplicate or near-duplicate of an existing question"],
            rewrite_instruction="fix duplicate",
            source_chunk_index=1,
            phase="fill",
        )
        assert rec["question_number"] == 3
        assert rec["attempt"] == 2
        assert rec["question"] == "What is currency?"
        assert rec["topic"] == "Currency"
        assert rec["sub_topic"] == "Definition"
        assert rec["target_difficulty"] == "easy"
        assert rec["answer_type"] == "single_correct"
        assert "duplicate" in rec["rejection_reasons"][0].lower()
        assert rec["source_chunk_index"] == 1
        assert rec["intent_fingerprint"]
        assert "chain" not in json.dumps(rec).lower()
        assert "reasoning" not in json.dumps(rec).lower()

    def test_matched_duplicate_metadata_persisted_when_available(self):
        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        match = find_lexical_duplicate_match(
            "What is currency used for?",
            [
                {
                    "id": "question_bank:abc",
                    "question": "What is currency used for in trade?",
                    "topic": "Currency",
                    "sub_topic": "Use",
                }
            ],
        )
        assert match is not None
        rec = build_rejected_attempt_record(
            slot=slot,
            attempt=1,
            generated={
                "question": "What is currency used for?",
                "topic": "Currency",
                "sub_topic": "Use",
            },
            rejection_reasons=["duplicate or near-duplicate of an existing question"],
            rewrite_instruction="dup",
            duplicate_match=match,
            source_chunk_index=0,
        )
        assert rec["duplicate_type"] in ("lexical", "exact")
        assert rec["matched_question_id"] == "question_bank:abc"
        assert "currency" in (rec["matched_stem"] or "").lower()
        assert rec["matched_intent_fingerprint"]
        assert rec["matched_topic"] == "Currency"

    def test_lexical_duplicate_retry_asks_different_intent_not_paraphrase(self):
        guidance = format_bank_batch_duplicate_retry_guidance(
            {
                "matched_topic": "Currency",
                "matched_intent_fingerprint": "currenc defin",
            }
        )
        assert "Do not paraphrase this question" in guidance
        assert "different learning objective" in guidance.lower() or "different" in guidance.lower()
        assert "skill" in guidance.lower() or "intent" in guidance.lower()
        assert "Avoid:" in guidance
        assert "topic=Currency" in guidance
        assert "Financial Literacy" not in guidance  # no hard-coded subject concepts
        # Final Paper guidance must remain distinct
        assert "Do not paraphrase this question" not in qp._REASON_GUIDANCE["duplicate"]

    def test_resolve_duplicate_rejection_preserves_difficulty_and_answer_type(self):
        slot = QuestionSlot(
            question_number=2,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="multiple_correct",
            grade="5",
            subject="Financial Literacy",
        )
        generated = {
            "question": "Which of these are functions of money?",
            "topic": "Functions of Money",
            "sub_topic": "Overview",
        }
        existing = [
            {
                "id": "question_bank:x",
                "question": "Which of these are functions of money in an economy?",
                "topic": "Functions of Money",
                "sub_topic": "Overview",
                "chapter": 1,
            }
        ]
        reasons, match, feedback = qp._resolve_duplicate_rejection(
            generated,
            slot,
            existing,
            ["duplicate or near-duplicate of an existing question"],
            bank_batch_mode=True,
        )
        assert slot.target_difficulty == "easy"
        assert slot.answer_type == "multiple_correct"
        assert "Do not paraphrase" in feedback
        assert "difficulty" not in feedback.lower() or "preserving the requested difficulty" in feedback
        assert match is not None

    def test_underused_topic_hint_is_bank_batch_only(self):
        usage = [
            {"topic": "Barter System", "sub_topic": "Limitations"},
            {"topic": "Barter System", "sub_topic": "Limitations"},
            {"topic": "Barter System", "sub_topic": "Limitations"},
            {"topic": "Currency", "sub_topic": "Definition"},
        ]
        catalog = {
            "sections": ["Unit of Account", "Store of Value"],
            "learning_outcomes": ["Identify unit of account examples"],
        }
        hints = format_underused_concept_hints(usage, catalog)
        assert "SOFT COVERAGE HINTS" in hints
        assert "Barter" in hints or "underused" in hints.lower()

        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "soft_coverage_hints" in gen_src
        soft_src = inspect.getsource(qp._bank_soft_coverage_hints)
        assert 'if not state.get("bank_batch_mode")' in soft_src
        assert "SOFT COVERAGE HINTS" not in qp.GENERATOR_SYSTEM

    @pytest.mark.asyncio
    async def test_final_paper_generate_has_no_soft_coverage_hints(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is X?",
                        "topic": "Money",
                        "sub_topic": "Coins",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "Because.",
                    }

            return R()

        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": False, "language": "en"},
                "chapter text",
                None,
                soft_coverage_hints="SOFT COVERAGE HINTS should not appear unless bank batch",
            )
        # soft_coverage_hints only applied when bank_batch_mode is True
        assert "SOFT COVERAGE HINTS" not in captured["system"]
        assert "SOFT COVERAGE HINTS" not in captured["user"]

    def test_diversity_planner_still_defaults_off(self, monkeypatch):
        monkeypatch.delenv("QUESTION_BANK_DIVERSITY_PLANNER", raising=False)
        assert is_bank_diversity_planner_enabled() is False

    def test_saturation_diagnostics_fields(self):
        sat = compute_bank_batch_saturation_diagnostics(
            seed_questions=[
                {"topic": "Barter", "sub_topic": "Limits", "question": "What is barter?"},
                {"topic": "Barter", "sub_topic": "Limits", "question": "Why did barter fail?"},
                {"topic": "Currency", "sub_topic": "Def", "question": "What is currency?"},
            ],
            approved=[
                {"topic": "Store of Value", "sub_topic": "Saving", "question": "Why save money?"}
            ],
            rejected_attempts=[
                {
                    "question_number": 1,
                    "attempt": 1,
                    "question": "What is currency?",
                    "duplicate_type": "lexical",
                    "rejection_reasons": ["duplicate or near-duplicate of an existing question"],
                    "intent_fingerprint": "currenc",
                },
                {
                    "question_number": 1,
                    "attempt": 2,
                    "question": "Which item stores value best?",
                    "duplicate_type": "semantic",
                    "rejection_reasons": [
                        "semantic duplicate: tests the same concept/intent as an accepted question"
                    ],
                    "intent_fingerprint": "item store valu",
                },
            ],
        )
        assert sat["existing_seed_count"] == 3
        assert sat["accepted_new_count"] == 1
        assert sat["duplicate_rejection_count"] >= 2
        assert sat["unique_topic_count"] >= 2
        assert sat["unique_sub_topic_count"] >= 2
        assert sat["unique_intent_count"] >= 1
        assert sat["most_repeated_topics"]
        assert sat["retries_that_changed_intent"] >= 1

    def test_final_paper_reason_guidance_unchanged_for_duplicates(self):
        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        fb = qp._build_reason_aware_feedback(
            ["duplicate or near-duplicate of an existing question"],
            previous_stems=[],
            accepted_topics=[],
            slot=slot,
            bank_batch_mode=False,
        )
        assert "Do not paraphrase this question" not in fb
        assert "DUPLICATE" in fb or "substantially DIFFERENT" in fb
        assert BANK_BATCH_DUPLICATE_RETRY_CORE not in fb

    def test_command_persists_rejected_attempts_field(self):
        from commands import question_paper_commands as qpc

        src = inspect.getsource(qpc.generate_question_bank_batch_command)
        assert "rejected_attempts" in src


class TestBankBatchStep4TargetRefill:
    """Step 4: strategy-aware missing-slot refill + bounded target cycle."""

    def test_attempt_budgets_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_target_refill_cycles_default_one(self, monkeypatch):
        monkeypatch.delenv("QUESTION_BANK_TARGET_REFILL_CYCLES", raising=False)
        assert bank_target_refill_cycles() == 1
        monkeypatch.setenv("QUESTION_BANK_TARGET_REFILL_CYCLES", "0")
        assert bank_target_refill_cycles() == 0
        monkeypatch.setenv("QUESTION_BANK_TARGET_REFILL_CYCLES", "2")
        assert bank_target_refill_cycles() == 2

    def test_needs_target_refill_allows_second_cycle(self):
        from open_notebook.graphs.question_bank_batch import _needs_target_refill

        base = {
            "bank_batch_mode": True,
            "approved": [{"validation_status": "passed"}] * 15,
            "failed_slots": [{"question_number": i} for i in range(16, 21)],
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=20, single_correct=16, multiple_correct=4
            ),
            "max_target_refill_cycles": 2,
        }
        # After cycle 1, still missing → allow cycle 2
        assert (
            _needs_target_refill({**base, "target_refill_cycles_done": 1})
            == "bank_target_refill"
        )
        # After cycle 2 budget exhausted → audit
        assert (
            _needs_target_refill({**base, "target_refill_cycles_done": 2})
            == "audit_bank_batch"
        )
        # No missing → audit even with budget
        assert (
            _needs_target_refill(
                {
                    **base,
                    "failed_slots": [],
                    "approved": [{"validation_status": "passed"}] * 20,
                    "target_refill_cycles_done": 1,
                }
            )
            == "audit_bank_batch"
        )

    def test_graph_loops_target_refill_conditionally(self):
        from open_notebook.graphs import question_bank_batch as qbb

        bank_src = inspect.getsource(qbb.build_question_bank_batch_graph)
        assert 'graph.add_conditional_edges(\n        "bank_target_refill"' in bank_src or (
            '"bank_target_refill"' in bank_src
            and "_needs_target_refill" in bank_src
        )
        # Must not unconditionally wire target → audit only (prevents multi-cycle)
        assert 'graph.add_edge("bank_target_refill", "audit_bank_batch")' not in bank_src

    @pytest.mark.asyncio
    async def test_target_cycle_only_refills_failed_and_records_history(self):
        from open_notebook.graphs import question_bank_batch as qbb

        approved = [
            {
                "question_number": i,
                "validation_status": "passed",
                "question": f"Accepted {i}",
                "answer_type": "single_correct",
                "target_difficulty": "easy",
            }
            for i in range(1, 16)
        ]
        failed = [
            {
                "question_number": 16,
                "validation_status": "needs_manual_review",
                "answer_type": "single_correct",
                "target_difficulty": "easy",
                "chapter": 1,
                "chapter_title": "Chapter 1",
                "grade": "5",
                "subject": "Financial Literacy",
            }
        ]
        seen_approved_ids = []

        async def fake_refill(state):
            # Must receive preserved approved and only failed slots
            assert len(state.get("approved") or []) == 15
            assert len(state.get("failed_slots") or []) == 1
            seen_approved_ids.append(id(state["approved"][0]))
            recovered = {
                **failed[0],
                "validation_status": "passed",
                "question": "Recovered Q16",
                "options": ["a", "b", "c", "d", "e"],
                "correct_indices": [0],
            }
            return {
                "approved": list(state["approved"]) + [recovered],
                "failed_slots": [],
                "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
                "cost_diagnostics": dict(state.get("cost_diagnostics") or {}),
            }

        state = {
            "bank_batch_mode": True,
            "approved": approved,
            "failed_slots": failed,
            "rejected_with_feedback": [
                {
                    "question_number": 16,
                    "question": "Old reject",
                    "rejection_reasons": ["duplicate or near-duplicate"],
                    "intent_fingerprint": "old",
                }
            ],
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=20, single_correct=16, multiple_correct=4
            ),
            "target_refill_cycles_done": 0,
            "max_target_refill_cycles": 2,
            "refill_diagnostics": {
                "accepted_after_normal_refill": 15,
                "target_cycle_history": [],
            },
            "chapter_chunks": {"1": ["chunk"]},
        }
        with patch.object(qbb, "refill_slots", side_effect=fake_refill):
            out = await qbb.bank_target_refill(state)

        assert len(out["approved"]) == 16
        assert out["failed_slots"] == []
        assert out["target_refill_cycles_done"] == 1
        hist = out["refill_diagnostics"]["target_cycle_history"]
        assert len(hist) == 1
        assert hist[0]["cycle"] == 1
        assert hist[0]["missing_before"] == 1
        assert hist[0]["newly_accepted"] == 1
        assert hist[0]["missing_after"] == 0
        assert out["refill_diagnostics"]["accepted_after_target_cycle_1"] == 16
        # Rejected history must be forwarded into refill state (via **state)
        assert len(state["rejected_with_feedback"]) == 1

    def test_slot_avoidance_history_aggregates_rejects(self):
        hist = build_slot_avoidance_history(
            [
                {
                    "question_number": 2,
                    "question": "What is barter?",
                    "topic": "Barter",
                    "sub_topic": "Definition",
                    "intent_fingerprint": "bart",
                    "source_chunk_index": 1,
                    "rejection_reasons": [
                        "duplicate or near-duplicate of an existing question"
                    ],
                    "matched_stem": "What was barter?",
                    "matched_intent_fingerprint": "bart",
                },
                {
                    "question_number": 2,
                    "question": "What is currency?",
                    "topic": "Currency",
                    "rejection_reasons": ["distractor quality failed"],
                    "source_chunk_index": 2,
                },
                {"question_number": 9, "question": "Other"},
            ],
            2,
        )
        assert "What is barter?" in hist["rejected_stems"]
        assert "bart" in hist["intent_fingerprints"]
        assert 1 in hist["chunk_indices"] and 2 in hist["chunk_indices"]
        assert hist["duplicate_reject_count"] >= 1
        assert hist["distractor_reject_count"] >= 1

    def test_classify_strategies(self):
        assert (
            classify_bank_refill_strategy(
                ["duplicate or near-duplicate"], {"duplicate_reject_count": 1}
            )
            == "duplicate"
        )
        assert (
            classify_bank_refill_strategy(
                ["semantic duplicate: same intent"], {"duplicate_reject_count": 3}
            )
            == "repeated_duplicate"
        )
        assert (
            classify_bank_refill_strategy(["unclear/irrelevant distractor(s): B"])
            == "distractor"
        )
        assert (
            classify_bank_refill_strategy(
                ["cognitive difficulty mismatch: target=easy, validated=medium"]
            )
            == "cognitive"
        )

    def test_strategy_guidance_preserves_difficulty_and_answer_type(self):
        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="multiple_correct",
            grade="5",
            subject="Financial Literacy",
        )
        for strategy in ("duplicate", "repeated_duplicate", "distractor", "cognitive"):
            text = format_bank_batch_strategy_guidance(
                strategy,
                slot=slot,
                avoidance={
                    "intent_fingerprints": ["currenc defin"],
                    "topics": ["Currency"],
                    "chunk_indices": [0, 1],
                },
            )
            assert "easy" in text
            assert "multiple_correct" in text
            assert "Medium" not in text or "target difficulty=easy" in text
            if strategy == "cognitive":
                assert "recognition" in text.lower() or "comprehension" in text.lower()
            if strategy == "distractor":
                assert "misconception" in text.lower()
            if strategy == "repeated_duplicate":
                assert "chunk" in text.lower()

    def test_chunk_avoidance_prefers_unused(self):
        chunks = ["A", "B", "C", "D"]
        excerpt, idx = select_chunk_avoiding_history(chunks, 0, 1, avoided_indices=[0, 1])
        assert idx not in (0, 1)
        assert excerpt in ("C", "D")

    def test_bank_graph_has_target_refill_and_final_paper_does_not(self):
        from open_notebook.graphs.question_bank_batch import (
            build_question_bank_batch_graph,
            _needs_target_refill,
        )
        from open_notebook.graphs.question_paper import build_question_paper_graph

        bank_src = inspect.getsource(build_question_bank_batch_graph)
        assert "bank_target_refill" in bank_src
        assert "mark_after_fill" in bank_src
        paper_src = inspect.getsource(build_question_paper_graph)
        assert "bank_target_refill" not in paper_src
        assert "mark_after_fill" not in paper_src

        # Terminates when accepted == requested
        state = {
            "bank_batch_mode": True,
            "approved": [{"validation_status": "passed"}] * 10,
            "failed_slots": [{"question_number": 11}],
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=10, single_correct=8, multiple_correct=2
            ),
            "target_refill_cycles_done": 0,
            "max_target_refill_cycles": 1,
        }
        assert _needs_target_refill(state) == "audit_bank_batch"

        # Terminates when budget exhausted
        state2 = {
            "bank_batch_mode": True,
            "approved": [{"validation_status": "passed"}] * 5,
            "failed_slots": [{"question_number": 6}],
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=10, single_correct=8, multiple_correct=2
            ),
            "target_refill_cycles_done": 1,
            "max_target_refill_cycles": 1,
        }
        assert _needs_target_refill(state2) == "audit_bank_batch"

        # Enters target when missing and budget remains
        state3 = {
            "bank_batch_mode": True,
            "approved": [{"validation_status": "passed"}] * 5,
            "failed_slots": [{"question_number": 6}],
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=10, single_correct=8, multiple_correct=2
            ),
            "target_refill_cycles_done": 0,
            "max_target_refill_cycles": 1,
        }
        assert _needs_target_refill(state3) == "bank_target_refill"

    def test_refill_only_processes_failed_slots_source(self):
        refill_src = inspect.getsource(qp.refill_slots)
        assert 'failed = state.get("failed_slots")' in refill_src
        assert "preserving" in refill_src.lower() or "never regenerat" in refill_src.lower()
        assert "format_bank_batch_strategy_guidance" in refill_src
        assert "select_chunk_avoiding_history" in refill_src

    def test_final_paper_refill_has_no_step4_strategy_by_default(self):
        # When bank_batch_mode is false, strategy guidance must not be required
        slot = QuestionSlot(
            question_number=1,
            chapter=1,
            chapter_title="Ch1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        fb = qp._build_reason_aware_feedback(
            ["duplicate or near-duplicate of an existing question"],
            previous_stems=[],
            accepted_topics=[],
            slot=slot,
            bank_batch_mode=False,
        )
        assert "REFILL STRATEGY" not in fb
        assert "Do not paraphrase this question" not in fb

    def test_diversity_planner_still_off_by_default(self, monkeypatch):
        monkeypatch.delenv("QUESTION_BANK_DIVERSITY_PLANNER", raising=False)
        assert is_bank_diversity_planner_enabled() is False


class TestBankBatchStep5CostAwareOrdering:
    """Step 5: cheap gates before blind/cognitive LLM (Bank Batch only)."""

    def _slot(self, **kwargs):
        base = dict(
            question_number=1,
            chapter=1,
            chapter_title="Chapter 1",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="5",
            subject="Financial Literacy",
        )
        base.update(kwargs)
        return QuestionSlot(**base)

    def _mcq(self, question="What is barter?", topic="Barter System", sub="Definition"):
        return {
            "question": question,
            "topic": topic,
            "sub_topic": sub,
            "options": [
                "Exchange of goods without money",
                "A type of bank account",
                "A government tax",
                "Digital payment only",
                "Interest on savings",
            ],
            "correct_indices": [0],
            "answer": "A",
            "explanation": "Barter is direct exchange of goods/services without money.",
        }

    def test_early_gates_detect_lexical_duplicate(self):
        from open_notebook.graphs.question_paper_blueprint import (
            run_bank_batch_early_gates,
        )

        slot = self._slot()
        stem = "What is currency in everyday life?"
        gen = self._mcq(stem, topic="Currency", sub="Meaning of Currency")
        reasons, cat = run_bank_batch_early_gates(
            slot=slot,
            generated=gen,
            existing_question_texts=[stem],
            existing_questions=[
                {
                    "chapter": 1,
                    "topic": "Currency",
                    "question": stem,
                }
            ],
        )
        assert cat == "duplicate"
        assert any("duplicate" in r.lower() for r in reasons)

    def test_early_gates_detect_metadata_failure(self):
        from open_notebook.graphs.question_paper_blueprint import (
            run_bank_batch_early_gates,
        )

        slot = self._slot()
        gen = self._mcq(topic="Financial Literacy", sub="")
        reasons, cat = run_bank_batch_early_gates(
            slot=slot,
            generated=gen,
            existing_question_texts=[],
            existing_questions=[],
        )
        assert cat == "metadata"
        assert reasons

    def test_early_gates_pass_clean_candidate(self):
        from open_notebook.graphs.question_paper_blueprint import (
            run_bank_batch_early_gates,
        )

        slot = self._slot()
        gen = self._mcq(
            question="Why were cowrie shells valued as early money?",
            topic="History of Money",
            sub="Cowrie Shells",
        )
        reasons, cat = run_bank_batch_early_gates(
            slot=slot,
            generated=gen,
            existing_question_texts=["What is a savings account?"],
            existing_questions=[
                {
                    "chapter": 1,
                    "topic": "Banking",
                    "question": "What is a savings account?",
                }
            ],
        )
        assert reasons == []
        assert cat is None

    @pytest.mark.asyncio
    async def test_duplicate_attempt_skips_blind_and_cognitive(self):
        slot = self._slot()
        seed = "What is the barter system?"
        generated = self._mcq(question="What is the barter system?")

        async def fake_gen(*_a, **_k):
            return generated

        async def boom_blind(*_a, **_k):
            raise AssertionError("blind solver must not run on early duplicate")

        async def boom_cog(*_a, **_k):
            raise AssertionError("cognitive validator must not run on early duplicate")

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "bank_duplicate_seed_texts": [seed],
            "bank_duplicate_seed_questions": [
                {"chapter": 1, "topic": "Barter", "question": seed}
            ],
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
        }
        with patch.object(qp, "_generate_for_slot", side_effect=fake_gen), patch.object(
            qp, "_blind_solve", side_effect=boom_blind
        ), patch.object(
            qp, "_validate_cognitive_quality", side_effect=boom_cog
        ):
            result = await qp.fill_slots(state)

        cost = result.get("cost_diagnostics") or {}
        assert cost.get("duplicate_early_exits", 0) >= 1
        assert cost.get("blind_solver_calls", 0) == 0
        assert cost.get("cognitive_quality_calls", 0) == 0
        assert cost.get("rejected_before_validator_llm", 0) >= 1

    @pytest.mark.asyncio
    async def test_metadata_failure_skips_expensive_validators(self):
        slot = self._slot()
        generated = self._mcq(topic="Financial Literacy", sub="Chapter 1")

        async def fake_gen(*_a, **_k):
            return generated

        async def boom_blind(*_a, **_k):
            raise AssertionError("blind solver must not run on metadata failure")

        async def boom_cog(*_a, **_k):
            raise AssertionError("cognitive must not run on metadata failure")

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Money content."]},
            "bank_batch_mode": True,
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
        }
        with patch.object(qp, "_generate_for_slot", side_effect=fake_gen), patch.object(
            qp, "_blind_solve", side_effect=boom_blind
        ), patch.object(
            qp, "_validate_cognitive_quality", side_effect=boom_cog
        ):
            result = await qp.fill_slots(state)

        cost = result.get("cost_diagnostics") or {}
        assert cost.get("metadata_early_exits", 0) >= 1
        assert cost.get("blind_solver_calls", 0) == 0
        assert cost.get("cognitive_quality_calls", 0) == 0

    @pytest.mark.asyncio
    async def test_non_duplicate_still_runs_all_validators(self):
        from open_notebook.graphs.question_paper_blueprint import (
            apply_independent_validation,
        )

        slot = self._slot()
        generated = self._mcq(
            question="Why were cowrie shells valued as early money?",
            topic="History of Money",
            sub="Cowrie Shells",
        )
        blind_calls = {"n": 0}
        cog_calls = {"n": 0}

        async def fake_gen(*_a, **_k):
            return generated

        async def fake_blind(*_a, **_k):
            blind_calls["n"] += 1

            class _R:
                def model_dump(self):
                    return {
                        "independently_derived_indices": [0],
                        "information_sufficient": True,
                        "arithmetic_consistent": True,
                        "no_unsupported_claims": True,
                        "terminology_grounded": True,
                        "option_analysis": [],
                    }

            return _R()

        async def fake_cog(*_a, **_k):
            cog_calls["n"] += 1
            scores = {c: 1 for c in qp.COGNITIVE_CRITERIA}
            flags = {
                "content_valid": True,
                "answer_valid": True,
                "grade_appropriate": True,
                "unambiguous": True,
                "language_clear": True,
                "explanation_valid": True,
                "distractors_ok": True,
                "grounded_in_material": True,
            }
            return scores, flags

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {
                "1": ["Cowrie shells were rare and valued as early money."]
            },
            "bank_batch_mode": True,
            "bank_duplicate_seed_texts": ["What is a savings account?"],
            "bank_duplicate_seed_questions": [
                {
                    "chapter": 1,
                    "topic": "Banking",
                    "question": "What is a savings account?",
                }
            ],
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
        }
        with patch.object(qp, "_generate_for_slot", side_effect=fake_gen), patch.object(
            qp, "_blind_solve", side_effect=fake_blind
        ), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            result = await qp.fill_slots(state)

        assert blind_calls["n"] == 1
        assert cog_calls["n"] == 1
        cost = result.get("cost_diagnostics") or {}
        assert cost.get("blind_solver_calls") == 1
        assert cost.get("cognitive_quality_calls") == 1
        # Surviving candidate still goes through apply_independent_validation
        # (acceptance criteria unchanged) — either accepted or rejected by quality.
        assert len(result.get("approved") or []) + len(
            result.get("failed_slots") or []
        ) == 1

    def test_final_paper_path_does_not_require_early_gates(self):
        fill_src = inspect.getsource(qp.fill_slots)
        # Early gates are gated behind bank_batch_mode
        assert "run_bank_batch_early_gates" in fill_src
        assert 'if state.get("bank_batch_mode")' in fill_src
        # Final Paper still has the prior lexical short-circuit branch
        assert "_is_external_duplicate" in fill_src

    def test_step4_budgets_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_cost_diagnostics_shape(self):
        from open_notebook.graphs.question_paper_blueprint import (
            empty_bank_cost_diagnostics,
            finalize_bank_cost_diagnostics,
        )

        d = empty_bank_cost_diagnostics()
        d["generated_attempts"] = 10
        d["blind_solver_calls"] = 3
        d["cognitive_quality_calls"] = 3
        out = finalize_bank_cost_diagnostics(d)
        assert out["total_llm_calls"] == 16
        assert "avg_latency_ms_per_stage" in out


class TestBankBatchStep6MultiCycleOffline:
    """
    Offline verification for Step 6 multi-cycle target refill.

    No LLM E2E — mocks refill_slots. Default cycles remain 1.
    """

    def _approved(self, n: int = 15):
        return [
            {
                "question_number": i,
                "validation_status": "passed",
                "question": f"Accepted stem {i}",
                "answer_type": "single_correct" if i <= 12 else "multiple_correct",
                "target_difficulty": "easy",
                "chapter": 1,
                "topic": f"Topic{i}",
            }
            for i in range(1, n + 1)
        ]

    def _failed(self, numbers, answer_type="single_correct"):
        return [
            {
                "question_number": n,
                "validation_status": "needs_manual_review",
                "answer_type": answer_type,
                "target_difficulty": "easy",
                "chapter": 1,
                "chapter_title": "Chapter 1",
                "grade": "5",
                "subject": "Financial Literacy",
            }
            for n in numbers
        ]

    def _base_state(self, approved, failed, *, cycles_done=0, max_cycles=2, rejected=None):
        return {
            "bank_batch_mode": True,
            "approved": approved,
            "failed_slots": failed,
            "rejected_with_feedback": list(rejected or []),
            "bank_batch_blueprint": _blueprint_dict(
                total_questions=20, single_correct=16, multiple_correct=4
            ),
            "target_refill_cycles_done": cycles_done,
            "max_target_refill_cycles": max_cycles,
            "refill_diagnostics": {
                "accepted_after_normal_refill": len(approved),
                "target_cycle_history": [],
            },
            "slot_avoidance_by_number": {},
            "chapter_chunks": {"1": ["chunk0", "chunk1", "chunk2"]},
            "language": "en",
        }

    def test_default_target_cycle_count_remains_one(self, monkeypatch):
        from open_notebook.graphs.question_paper_blueprint import (
            DEFAULT_TARGET_REFILL_CYCLES,
        )

        monkeypatch.delenv("QUESTION_BANK_TARGET_REFILL_CYCLES", raising=False)
        assert DEFAULT_TARGET_REFILL_CYCLES == 1
        assert bank_target_refill_cycles() == 1

    def test_stops_when_requested_count_reached(self):
        from open_notebook.graphs.question_bank_batch import _needs_target_refill

        state = self._base_state(self._approved(20), [], cycles_done=1, max_cycles=2)
        assert _needs_target_refill(state) == "audit_bank_batch"

    def test_max_configured_cycles_respected(self):
        from open_notebook.graphs.question_bank_batch import _needs_target_refill

        state = self._base_state(
            self._approved(15),
            self._failed([16, 17, 18, 19, 20]),
            cycles_done=2,
            max_cycles=2,
        )
        assert _needs_target_refill(state) == "audit_bank_batch"
        # With budget remaining, continue
        state["target_refill_cycles_done"] = 1
        assert _needs_target_refill(state) == "bank_target_refill"

    def test_no_infinite_loop_when_max_zero(self):
        from open_notebook.graphs.question_bank_batch import _needs_target_refill

        state = self._base_state(
            self._approved(10),
            self._failed([11]),
            cycles_done=0,
            max_cycles=0,
        )
        assert _needs_target_refill(state) == "audit_bank_batch"

    def test_final_paper_unchanged(self):
        from open_notebook.graphs import question_paper as qp_mod
        from open_notebook.graphs import question_bank_batch as qbb

        paper_src = inspect.getsource(qp_mod.build_question_paper_graph)
        assert "bank_target_refill" not in paper_src
        assert "max_target_refill_cycles" not in paper_src
        bank_src = inspect.getsource(qbb.build_question_bank_batch_graph)
        assert "bank_target_refill" in bank_src

    @pytest.mark.asyncio
    async def test_cycle2_receives_only_failed_slots_and_preserves_accepted(self):
        from open_notebook.graphs import question_bank_batch as qbb

        approved = self._approved(15)
        failed = self._failed([16, 17, 18, 19, 20])
        approved_snapshot = [dict(q) for q in approved]
        calls = {"n": 0}

        async def fake_refill(state):
            calls["n"] += 1
            assert len(state["approved"]) == 15
            assert {q["question_number"] for q in state["failed_slots"]} == {
                16,
                17,
                18,
                19,
                20,
            }
            # Must not regenerate accepted stems
            for a, b in zip(state["approved"], approved_snapshot):
                assert a["question"] == b["question"]
                assert a["target_difficulty"] == "easy"
                assert a["answer_type"] == b["answer_type"]
            # Recover one missing slot only
            recovered = {
                **failed[0],
                "validation_status": "passed",
                "question": "Recovered 16",
                "options": ["a", "b", "c", "d", "e"],
                "correct_indices": [0],
                "target_difficulty": "easy",
                "answer_type": "single_correct",
            }
            return {
                "approved": list(state["approved"]) + [recovered],
                "failed_slots": list(state["failed_slots"][1:]),
                "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
            }

        state = self._base_state(approved, failed, cycles_done=0, max_cycles=2)
        with patch.object(qbb, "refill_slots", side_effect=fake_refill):
            out1 = await qbb.bank_target_refill(state)

        assert calls["n"] == 1
        assert len(out1["approved"]) == 16
        assert len(out1["failed_slots"]) == 4
        assert out1["target_refill_cycles_done"] == 1
        # Original 15 accepted stems untouched
        for a, b in zip(out1["approved"][:15], approved_snapshot):
            assert a["question"] == b["question"]

        # Cycle 2: only remaining 4 failed
        state2 = {
            **state,
            **out1,
            "target_refill_cycles_done": 1,
        }

        async def fake_refill_c2(s):
            calls["n"] += 1
            assert len(s["approved"]) == 16
            assert {q["question_number"] for q in s["failed_slots"]} == {17, 18, 19, 20}
            for q in s["approved"][:15]:
                assert q["question"].startswith("Accepted stem")
            assert s["approved"][15]["question"] == "Recovered 16"
            return {
                "approved": list(s["approved"]),
                "failed_slots": list(s["failed_slots"]),
                "rejected_with_feedback": list(s.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(s.get("refill_diagnostics") or {}),
            }

        with patch.object(qbb, "refill_slots", side_effect=fake_refill_c2):
            out2 = await qbb.bank_target_refill(state2)

        assert calls["n"] == 2
        assert out2["target_refill_cycles_done"] == 2
        hist = out2["refill_diagnostics"]["target_cycle_history"]
        assert len(hist) == 2
        assert hist[0]["cycle"] == 1 and hist[0]["newly_accepted"] == 1
        assert hist[0]["missing_before"] == 5 and hist[0]["missing_after"] == 4
        assert hist[1]["cycle"] == 2 and hist[1]["missing_before"] == 4
        assert out2["refill_diagnostics"]["accepted_after_target_cycle_1"] == 16
        assert out2["refill_diagnostics"]["accepted_after_target_cycle_2"] == 16

    @pytest.mark.asyncio
    async def test_difficulty_and_answer_type_fixed_into_refill(self):
        from open_notebook.graphs import question_bank_batch as qbb

        approved = self._approved(18)
        failed = self._failed([19], answer_type="multiple_correct")
        failed[0]["target_difficulty"] = "easy"
        captured = {}

        async def fake_refill(state):
            slot_fail = state["failed_slots"][0]
            captured["difficulty"] = slot_fail["target_difficulty"]
            captured["answer_type"] = slot_fail["answer_type"]
            # refill_slots asserts frozen constraints; we mirror that contract
            assert slot_fail["target_difficulty"] == "easy"
            assert slot_fail["answer_type"] == "multiple_correct"
            return {
                "approved": list(state["approved"]),
                "failed_slots": list(state["failed_slots"]),
                "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
            }

        state = self._base_state(approved, failed, max_cycles=2)
        with patch.object(qbb, "refill_slots", side_effect=fake_refill):
            await qbb.bank_target_refill(state)
        assert captured == {"difficulty": "easy", "answer_type": "multiple_correct"}

    @pytest.mark.asyncio
    async def test_avoidance_and_duplicate_and_chunk_history_carry_to_cycle2(self):
        from open_notebook.graphs import question_bank_batch as qbb

        approved = self._approved(15)
        failed = self._failed([16, 17])
        rejected_c1 = [
            {
                "question_number": 16,
                "question": "What is barter system?",
                "topic": "Barter",
                "sub_topic": "Definition",
                "intent_fingerprint": "bart system",
                "source_chunk_index": 0,
                "rejection_reasons": [
                    "duplicate or near-duplicate of an existing question"
                ],
                "matched_stem": "What is barter?",
                "matched_intent_fingerprint": "bart",
                "duplicate_type": "lexical",
            },
            {
                "question_number": 16,
                "question": "Explain currency exchange briefly",
                "topic": "Currency Exchange",
                "sub_topic": "Process",
                "intent_fingerprint": "currenc exchang",
                "source_chunk_index": 2,
                "rejection_reasons": ["cognitive difficulty mismatch"],
                "matched_stem": "",
            },
        ]

        async def fake_c1(state):
            # Recover none; append another reject so cycle-2 sees accumulated log
            more = list(state.get("rejected_with_feedback") or []) + [
                {
                    "question_number": 17,
                    "question": "Define denominations",
                    "topic": "Denominations",
                    "sub_topic": "Meaning",
                    "intent_fingerprint": "denomin",
                    "source_chunk_index": 1,
                    "rejection_reasons": ["semantic duplicate: same intent"],
                    "matched_stem": "What are denominations?",
                    "matched_intent_fingerprint": "denomin",
                    "duplicate_type": "semantic",
                }
            ]
            return {
                "approved": list(state["approved"]),
                "failed_slots": list(state["failed_slots"]),
                "rejected_with_feedback": more,
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
            }

        state = self._base_state(
            approved, failed, rejected=rejected_c1, cycles_done=0, max_cycles=2
        )
        with patch.object(qbb, "refill_slots", side_effect=fake_c1):
            out1 = await qbb.bank_target_refill(state)

        carried = out1["rejected_with_feedback"]
        assert len(carried) == 3
        hist16 = build_slot_avoidance_history(carried, 16)
        hist17 = build_slot_avoidance_history(carried, 17)
        assert "bart system" in hist16["intent_fingerprints"]
        assert "What is barter?" in hist16["matched_stems"] or any(
            "barter" in (s or "").lower() for s in hist16["matched_stems"]
        )
        assert 0 in hist16["chunk_indices"] and 2 in hist16["chunk_indices"]
        assert "Barter" in hist16["topics"] and "Currency Exchange" in hist16["topics"]
        assert hist16["duplicate_reject_count"] >= 1
        assert "denomin" in hist17["intent_fingerprints"]
        assert 1 in hist17["chunk_indices"]

        captured_c2 = {}

        async def fake_c2(s):
            captured_c2["rejected"] = list(s.get("rejected_with_feedback") or [])
            captured_c2["failed_nums"] = [
                f["question_number"] for f in s.get("failed_slots") or []
            ]
            # Cycle 2 must see full accumulated rejection log from cycle 1
            assert len(captured_c2["rejected"]) == 3
            h = build_slot_avoidance_history(captured_c2["rejected"], 16)
            assert h["duplicate_reject_count"] >= 1
            assert set(h["chunk_indices"]) >= {0, 2}
            return {
                "approved": list(s["approved"]),
                "failed_slots": list(s["failed_slots"]),
                "rejected_with_feedback": captured_c2["rejected"],
                "refill_diagnostics": dict(s.get("refill_diagnostics") or {}),
            }

        state2 = {**state, **out1, "target_refill_cycles_done": 1}
        with patch.object(qbb, "refill_slots", side_effect=fake_c2):
            out2 = await qbb.bank_target_refill(state2)

        assert captured_c2["failed_nums"] == [16, 17]
        assert out2["target_refill_cycles_done"] == 2

    @pytest.mark.asyncio
    async def test_skip_immediately_when_already_complete(self):
        from open_notebook.graphs import question_bank_batch as qbb

        state = self._base_state(self._approved(20), [], cycles_done=0, max_cycles=2)
        with patch.object(qbb, "refill_slots", AsyncMock()) as mock_refill:
            out = await qbb.bank_target_refill(state)
        mock_refill.assert_not_called()
        assert out["target_refill_cycles_done"] == 0
        assert out["refill_diagnostics"]["accepted_after_target_refill"] == 20

    @pytest.mark.asyncio
    async def test_per_cycle_diagnostics_accurate_two_cycles(self):
        from open_notebook.graphs import question_bank_batch as qbb

        approved = self._approved(15)
        failed = self._failed([16, 17, 18, 19, 20])

        async def fake_c1(state):
            recovered = [
                {
                    **failed[i],
                    "validation_status": "passed",
                    "question": f"New {failed[i]['question_number']}",
                    "options": ["a", "b", "c", "d", "e"],
                    "correct_indices": [0],
                }
                for i in range(3)  # recover 16,17,18
            ]
            return {
                "approved": list(state["approved"]) + recovered,
                "failed_slots": failed[3:],
                "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
            }

        async def fake_c2(state):
            recovered = {
                **state["failed_slots"][0],
                "validation_status": "passed",
                "question": "New 19",
                "options": ["a", "b", "c", "d", "e"],
                "correct_indices": [0],
            }
            return {
                "approved": list(state["approved"]) + [recovered],
                "failed_slots": state["failed_slots"][1:],
                "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
                "refill_diagnostics": dict(state.get("refill_diagnostics") or {}),
            }

        state = self._base_state(approved, failed, max_cycles=2)
        with patch.object(qbb, "refill_slots", side_effect=fake_c1):
            out1 = await qbb.bank_target_refill(state)
        h1 = out1["refill_diagnostics"]["target_cycle_history"][0]
        assert h1["cycle"] == 1
        assert h1["missing_before"] == 5
        assert h1["newly_accepted"] == 3
        assert h1["missing_after"] == 2
        assert h1["accepted_before"] == 15
        assert h1["accepted_after"] == 18
        assert isinstance(h1["runtime_s"], (int, float))

        state2 = {**state, **out1, "target_refill_cycles_done": 1}
        with patch.object(qbb, "refill_slots", side_effect=fake_c2):
            out2 = await qbb.bank_target_refill(state2)
        hist = out2["refill_diagnostics"]["target_cycle_history"]
        assert len(hist) == 2
        assert hist[1]["cycle"] == 2
        assert hist[1]["missing_before"] == 2
        assert hist[1]["newly_accepted"] == 1
        assert hist[1]["missing_after"] == 1
        assert hist[1]["accepted_after"] == 19
        assert out2["refill_diagnostics"]["target_refill_cycles_run"] == 2
        assert out2["refill_diagnostics"]["accepted_after_target_cycle_1"] == 18
        assert out2["refill_diagnostics"]["accepted_after_target_cycle_2"] == 19

        # After cycle 2 still missing → routing would allow more only if max>2
        from open_notebook.graphs.question_bank_batch import _needs_target_refill

        assert (
            _needs_target_refill(
                {
                    **out2,
                    "bank_batch_mode": True,
                    "bank_batch_blueprint": state["bank_batch_blueprint"],
                    "max_target_refill_cycles": 2,
                }
            )
            == "audit_bank_batch"
        )

    def test_refill_slots_source_never_regenerates_approved(self):
        refill_src = inspect.getsource(qp.refill_slots)
        assert "never regenerat" in refill_src.lower() or "preserving" in refill_src.lower()
        assert "approved_ids" in refill_src
        assert "failed = state.get(\"failed_slots\")" in refill_src

class TestBankBatchIntentPlannerStep7:
    """Step 7: pre-generation intent planning — Bank Batch only."""

    def _chunks(self):
        return [
            "Currency includes coins, paper notes, and digital money. Money is a broader concept.",
            "Barter is direct exchange of goods without money. Double coincidence of wants is a problem.",
            "Banks accept deposits and give loans. Savings accounts help people store money safely.",
        ]

    def _intent(self, **kwargs):
        base = {
            "intent_id": kwargs.get("intent_id", "i1"),
            "topic": kwargs.get("topic", "Currency"),
            "sub_topic": kwargs.get("sub_topic", "Definition"),
            "concept": kwargs.get("concept", "currency"),
            "objective": kwargs.get("objective", "define currency"),
            "cognitive_form": kwargs.get("cognitive_form", "recall a taught fact"),
            "source_section": kwargs.get("source_section", "Currency"),
            "chunk_index": kwargs.get("chunk_index", 0),
        }
        from open_notebook.graphs.question_bank_intent import (
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        n = normalize_intent_dict(base)
        n["intent_fingerprint"] = planned_intent_fingerprint(n)
        return n

    def test_intent_helpers_bank_batch_only_in_prepare(self):
        import open_notebook.graphs.question_bank_batch as qbb

        prep = inspect.getsource(qbb.prepare_bank_batch)
        assert "build_or_load_base_intent_catalog" in prep
        assert "bank_intent_assignments" in prep
        # Final Paper prepare_blueprint path must not call intent catalog builder
        paper_src = inspect.getsource(qp)
        # prepare_bank_batch is imported into bank batch module only
        assert "async def prepare_bank_batch" not in inspect.getsource(qp.fill_slots)
    def test_final_paper_generate_has_no_intent_block_without_flag(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "intent_guidance" in gen_src
        assert "bank_batch_mode and intent_guidance" in gen_src.replace("\n", " ")

    def test_ungrounded_intent_discarded(self):
        from open_notebook.graphs.question_bank_intent import ground_intent

        bad = self._intent(
            concept="quantum entanglement",
            objective="explain quantum entanglement",
            chunk_index=0,
        )
        assert ground_intent(bad, self._chunks()) is None

    def test_grounded_intent_kept_and_chunk_validated(self):
        from open_notebook.graphs.question_bank_intent import ground_intent

        good = self._intent(
            concept="currency",
            objective="identify that currency includes digital money",
            chunk_index=0,
        )
        g = ground_intent(good, self._chunks())
        assert g is not None
        assert g["chunk_index"] == 0

    def test_same_topic_different_objective_allowed(self):
        from open_notebook.graphs.question_bank_intent import (
            filter_intents_against_used,
            intents_share_objective,
        )

        a = self._intent(objective="define currency", concept="currency")
        b = self._intent(
            intent_id="i2",
            objective="distinguish currency from money",
            concept="currency",
        )
        assert intents_share_objective(a, b) is False
        available, filtered = filter_intents_against_used(
            [a, b],
            bank_questions=[],
        )
        assert len(available) == 2
        assert filtered == 0

    def test_same_objective_paraphrase_filtered(self):
        from open_notebook.graphs.question_bank_intent import (
            filter_intents_against_used,
            intents_share_objective,
        )

        a = self._intent(objective="define currency", concept="currency")
        b = self._intent(
            intent_id="i2",
            objective="what does currency mean",
            concept="currency",
        )
        assert intents_share_objective(a, b) is True
        available, filtered = filter_intents_against_used([b], bank_questions=[
            {"question": "What is the definition of currency?", "topic": "Currency"}
        ])
        assert filtered == 1
        assert available == []

    def test_existing_bank_intent_filtered_before_generation(self):
        from open_notebook.graphs.question_bank_intent import filter_intents_against_used

        planned = self._intent(objective="define currency", concept="currency")
        bank = [
            {
                "question": "What does currency mean in this chapter?",
                "topic": "Currency",
                "chapter": 1,
            }
        ]
        available, filtered = filter_intents_against_used([planned], bank_questions=bank)
        assert filtered == 1
        assert available == []

    def test_current_batch_assigned_intent_not_reused(self):
        from open_notebook.graphs.question_bank_intent import filter_intents_against_used

        a = self._intent(intent_id="a", objective="define barter", concept="barter")
        b = self._intent(intent_id="b", objective="define barter", concept="barter")
        available, filtered = filter_intents_against_used(
            [b],
            assigned_intents=[a],
        )
        assert filtered == 1
        assert available == []

    def test_duplicate_rejection_retires_and_replans(self):
        from open_notebook.graphs.question_bank_intent import (
            rejection_is_duplicate,
            take_next_unused_intent,
        )

        assert rejection_is_duplicate(["duplicate or near-duplicate of an existing question"])
        remaining = [
            self._intent(intent_id="next", objective="identify barter problem", concept="barter", chunk_index=1)
        ]
        nxt = take_next_unused_intent(remaining, retired_ids={"old"})
        assert nxt is not None
        assert nxt["intent_id"] == "next"
        assert remaining == []

    def test_distractor_failure_retries_same_intent(self):
        from open_notebook.graphs.question_bank_intent import (
            rejection_is_distractor_or_answer,
            rejection_is_duplicate,
        )

        reasons = ["unclear/irrelevant distractor(s): E"]
        assert rejection_is_distractor_or_answer(reasons)
        assert not rejection_is_duplicate(reasons)

    def test_cognitive_mismatch_preserves_difficulty_hint(self):
        from open_notebook.graphs.question_bank_intent import (
            cognitive_form_correction_hint,
            rejection_is_cognitive,
        )

        assert rejection_is_cognitive(
            ["cognitive difficulty mismatch: target=easy, validated=medium (score=15)"]
        )
        hint = cognitive_form_correction_hint(self._intent(), "easy")
        assert "difficulty=easy" in hint
        assert "currency" in hint.lower()
        assert "Keep concept/objective" in hint

    def test_answer_type_remains_fixed_in_intent_guidance(self):
        from open_notebook.graphs.question_bank_intent import format_assigned_intent_guidance

        g = format_assigned_intent_guidance(self._intent())
        assert "ASSIGNED QUESTION INTENT" in g
        assert "objective" in g
        assert "REQUIRED" in g
        # Guidance must not suggest changing answer type / difficulty
        assert "change answer_type" not in g.lower()
        assert "Do NOT replace the assigned objective" in g

    def test_assign_intents_to_slots(self):
        from open_notebook.graphs.question_bank_intent import assign_intents_to_slots
        from open_notebook.graphs.question_paper_blueprint import QuestionSlot

        slots = [
            QuestionSlot(
                question_number=1,
                chapter=1,
                chapter_title="Ch1",
                target_difficulty="easy",
                answer_type="single_correct",
                grade="5",
                subject="Financial Literacy",
            ),
            QuestionSlot(
                question_number=2,
                chapter=1,
                chapter_title="Ch1",
                target_difficulty="easy",
                answer_type="single_correct",
                grade="5",
                subject="Financial Literacy",
            ),
        ]
        catalog = [
            self._intent(intent_id="a", objective="define currency"),
            self._intent(intent_id="b", objective="identify barter", concept="barter", chunk_index=1),
            self._intent(intent_id="c", objective="recognize banks", concept="banks", chunk_index=2),
        ]
        assignments, remaining, n = assign_intents_to_slots(slots, catalog)
        assert n == 2
        assert set(assignments.keys()) == {"1", "2"}
        assert len(remaining) == 1

    def test_catalog_exhaustion_falls_back_safely(self):
        from open_notebook.graphs.question_bank_intent import (
            assign_intents_to_slots,
            take_next_unused_intent,
        )
        from open_notebook.graphs.question_paper_blueprint import QuestionSlot

        slots = [
            QuestionSlot(
                question_number=i,
                chapter=1,
                chapter_title="Ch1",
                target_difficulty="easy",
                answer_type="single_correct",
                grade="5",
                subject="FL",
            )
            for i in range(1, 4)
        ]
        assignments, remaining, n = assign_intents_to_slots(
            slots, [self._intent(intent_id="only")]
        )
        assert n == 1
        assert len(assignments) == 1
        assert take_next_unused_intent(remaining) is None

    def test_cached_catalog_reused_and_content_change_invalidates(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        key1 = ib.intent_cache_key(
            book_id="book:1",
            chapter=1,
            difficulty="easy",
            content_hash=ib.chapter_content_hash("text A"),
        )
        key2 = ib.intent_cache_key(
            book_id="book:1",
            chapter=1,
            difficulty="easy",
            content_hash=ib.chapter_content_hash("text B different"),
        )
        assert key1 != key2
        intents = [self._intent()]
        ib.save_cached_intent_catalog(key1, intents)
        loaded = ib.load_cached_intent_catalog(key1)
        assert loaded is not None
        assert len(loaded) == 1
        assert ib.load_cached_intent_catalog(key2) is None

    def test_intent_planner_default_on_diversity_off_cycles_one(self, monkeypatch):
        from open_notebook.graphs.question_bank_intent import is_bank_intent_planner_enabled
        from open_notebook.graphs.question_paper_blueprint import (
            bank_target_refill_cycles,
            is_bank_diversity_planner_enabled,
        )

        monkeypatch.delenv("QUESTION_BANK_INTENT_PLANNER", raising=False)
        monkeypatch.delenv("QUESTION_BANK_DIVERSITY_PLANNER", raising=False)
        monkeypatch.delenv("QUESTION_BANK_TARGET_REFILL_CYCLES", raising=False)
        assert is_bank_intent_planner_enabled() is True
        assert is_bank_diversity_planner_enabled() is False
        assert bank_target_refill_cycles() == 1

    def test_ground_intent_catalog_discards_ungrounded(self):
        from open_notebook.graphs.question_bank_intent import ground_intent_catalog

        raw = [
            self._intent(concept="currency", objective="define currency", chunk_index=0),
            self._intent(
                intent_id="bad",
                concept="photosynthesis",
                objective="explain photosynthesis",
                chunk_index=0,
            ),
        ]
        grounded, discarded = ground_intent_catalog(raw, self._chunks())
        assert len(grounded) == 1
        assert discarded >= 1


class TestBankBatchIntentAlignmentStep7B:
    """Step 7B: bank intent derivation, adherence gate, shared normalization."""

    def _intent(self, **kwargs):
        base = {
            "intent_id": kwargs.get("intent_id", "i1"),
            "topic": kwargs.get("topic", "Currency"),
            "sub_topic": kwargs.get("sub_topic", "Definition"),
            "concept": kwargs.get("concept", "currency"),
            "objective": kwargs.get("objective", "define currency"),
            "cognitive_form": kwargs.get("cognitive_form", "recall a taught fact"),
            "source_section": kwargs.get("source_section", "Currency"),
            "chunk_index": kwargs.get("chunk_index", 0),
        }
        from open_notebook.graphs.question_bank_intent import (
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        n = normalize_intent_dict(base)
        n["intent_fingerprint"] = planned_intent_fingerprint(n)
        return n

    def test_existing_bank_question_gets_derived_intent_metadata(self):
        from open_notebook.graphs.question_bank_intent import (
            derive_intent_from_bank_question,
            enrich_bank_questions_with_intents,
        )

        seed = {
            "id": "question_bank:seed1",
            "question": "What does currency mean in this chapter?",
            "topic": "Currency",
            "sub_topic": "Definition",
            "chapter": 1,
        }
        derived = derive_intent_from_bank_question(seed, use_cache=False)
        assert derived["concept"]
        assert derived["objective"]
        assert derived["cognitive_form"]
        assert derived["intent_fingerprint"]
        assert "currency" in derived["objective"].lower() or "currency" in derived["concept"].lower()
        # Historical wording unchanged on original
        assert seed["question"] == "What does currency mean in this chapter?"
        enriched, n = enrich_bank_questions_with_intents([seed])
        assert n == 1
        assert enriched[0]["question"] == seed["question"]
        assert enriched[0]["intent_fingerprint"]

    def test_derived_and_planner_intent_same_normalization(self):
        from open_notebook.graphs.question_bank_intent import (
            derive_intent_from_bank_question,
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        planned = normalize_intent_dict(
            {
                "concept": "currency",
                "objective": "define currency",
                "cognitive_form": "recall a taught fact",
                "topic": "Currency",
            }
        )
        bank = derive_intent_from_bank_question(
            {
                "question": "What does currency mean?",
                "topic": "Currency",
                "sub_topic": "Definition",
            },
            use_cache=False,
        )
        assert set(planned.keys()) >= {
            "concept",
            "objective",
            "cognitive_form",
            "intent_fingerprint",
        }
        assert set(bank.keys()) >= {
            "concept",
            "objective",
            "cognitive_form",
            "intent_fingerprint",
        }
        assert planned["intent_fingerprint"] == planned_intent_fingerprint(planned)
        assert bank["intent_fingerprint"] == planned_intent_fingerprint(bank)

    def test_same_objective_paraphrase_prefiltered_via_derived_bank(self):
        from open_notebook.graphs.question_bank_intent import (
            filter_intents_against_used,
            intents_share_objective,
        )

        planned = self._intent(objective="define currency", concept="currency")
        bank = [
            {
                "question": "What does currency mean?",
                "topic": "Currency",
                "sub_topic": "Definition",
            }
        ]
        assert intents_share_objective(
            planned,
            {
                "concept": "Currency",
                "objective": "Define currency",
            },
        )
        available, filtered = filter_intents_against_used([planned], bank_questions=bank)
        assert filtered == 1
        assert available == []

    def test_same_topic_different_objective_still_allowed(self):
        from open_notebook.graphs.question_bank_intent import (
            filter_intents_against_used,
            intents_share_objective,
        )

        define = self._intent(objective="define currency", concept="currency")
        distinguish = self._intent(
            intent_id="i2",
            objective="distinguish currency from money",
            concept="currency",
            cognitive_form="distinguish two taught concepts",
        )
        assert intents_share_objective(define, distinguish) is False
        bank = [
            {
                "question": "What does currency mean?",
                "topic": "Currency",
                "sub_topic": "Definition",
            }
        ]
        available, filtered = filter_intents_against_used(
            [define, distinguish], bank_questions=bank
        )
        assert filtered == 1
        assert len(available) == 1
        assert "distinguish" in available[0]["objective"].lower()

    def test_drifted_generation_rejected_early(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_DRIFTED,
            INTENT_DRIFT_REJECTION,
            classify_intent_adherence,
        )

        assigned = self._intent(
            concept="store of value",
            objective="Recall the function of money that allows people to save",
        )
        generated = {
            "question": "Why did people in ancient times start using metal coins instead of barter?",
            "topic": "History of Money",
        }
        assert classify_intent_adherence(assigned, generated) == ADHERENCE_DRIFTED
        assert "assigned objective" in INTENT_DRIFT_REJECTION

    def test_generator_retry_preserves_assigned_intent_on_drift(self):
        """Drift feedback keeps same intent; replan only on duplicate."""
        from open_notebook.graphs.question_bank_intent import (
            INTENT_DRIFT_REJECTION,
            intent_drift_feedback,
            rejection_is_duplicate,
        )
        import open_notebook.graphs.question_paper as qp_mod

        assigned = self._intent()
        fb = intent_drift_feedback(assigned)
        assert "SAME assigned intent" in fb
        assert assigned["objective"] in fb
        assert rejection_is_duplicate([INTENT_DRIFT_REJECTION]) is False
        # fill path wires drift before early gates and does not retire on drift
        fill_src = inspect.getsource(qp_mod.fill_slots)
        assert "classify_intent_adherence" in fill_src
        assert "intent_drift_feedback" in fill_src
        assert "should_early_reject_for_intent_drift" in fill_src
        assert "partial_adherence_may_continue" in fill_src
        refill_src = inspect.getsource(qp_mod.refill_slots)
        assert "classify_intent_adherence" in refill_src
        assert "partial_adherence_may_continue" in refill_src

    def test_valid_adherence_continues_to_normal_validators(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_STRONG,
            classify_intent_adherence,
        )

        assigned = self._intent(objective="define currency", concept="currency")
        generated = {
            "question": "What does the term currency mean?",
            "topic": "Currency",
        }
        assert classify_intent_adherence(assigned, generated) == ADHERENCE_STRONG


class TestBankBatchIntentAdherenceStep7C:
    """Step 7C: PARTIAL continues; only TRUE DRIFT early-exits."""

    def _intent(self, **kwargs):
        from open_notebook.graphs.question_bank_intent import (
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        base = {
            "intent_id": kwargs.get("intent_id", "i1"),
            "topic": kwargs.get("topic", "Currency"),
            "sub_topic": kwargs.get("sub_topic", "Definition"),
            "concept": kwargs.get("concept", "currency"),
            "objective": kwargs.get("objective", "define currency"),
            "cognitive_form": kwargs.get("cognitive_form", "recall a taught fact"),
            "chunk_index": kwargs.get("chunk_index", 0),
        }
        n = normalize_intent_dict(base)
        n["intent_fingerprint"] = planned_intent_fingerprint(n)
        return n

    def test_strong_adherence_continues(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_STRONG,
            classify_intent_adherence,
            should_early_reject_for_intent_drift,
        )

        assigned = self._intent()
        generated = {"question": "What does the term currency mean?", "topic": "Currency"}
        assert classify_intent_adherence(assigned, generated) == ADHERENCE_STRONG
        assert should_early_reject_for_intent_drift(ADHERENCE_STRONG) is False

    def test_partial_same_concept_objective_continues(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_PARTIAL,
            ADHERENCE_STRONG,
            classify_intent_adherence,
            partial_adherence_may_continue,
            should_early_reject_for_intent_drift,
        )

        assigned = self._intent(
            concept="denominations",
            objective="Identify denominations as different values of money",
            cognitive_form="identify a concept",
        )
        generated = {
            "question": "In India's currency system, ₹1, ₹5, ₹10, and ₹20 are examples of what?",
            "topic": "Denominations",
            "sub_topic": "Indian Currency Denominations",
        }
        label = classify_intent_adherence(assigned, generated)
        assert label in (ADHERENCE_PARTIAL, ADHERENCE_STRONG)
        if label == ADHERENCE_PARTIAL:
            assert partial_adherence_may_continue(
                assigned,
                generated,
                target_difficulty="easy",
                answer_type="single_correct",
            )
        assert should_early_reject_for_intent_drift(label) is False

    def test_true_drift_still_exits_early(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_DRIFTED,
            classify_intent_adherence,
            should_early_reject_for_intent_drift,
        )

        assigned = self._intent(
            concept="store of value",
            objective="Recall the function of money that allows people to save for the future",
        )
        generated = {
            "question": "Why did people in ancient times start using metal coins instead of barter?",
            "topic": "History of Money",
        }
        assert classify_intent_adherence(assigned, generated) == ADHERENCE_DRIFTED
        assert should_early_reject_for_intent_drift(ADHERENCE_DRIFTED) is True

    def test_wording_differences_alone_do_not_cause_drift_rejection(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_DRIFTED,
            classify_intent_adherence,
            should_early_reject_for_intent_drift,
        )

        assigned = self._intent(
            concept="exchange rates",
            objective="Identify that exchange rates determine how currencies are converted",
            cognitive_form="identify a concept",
        )
        generated = {
            "question": (
                "When you travel to another country, you need to convert your home "
                "currency into the local currency. What determines how much you get?"
            ),
            "topic": "Currency Exchange",
            "sub_topic": "Exchange Rates",
        }
        label = classify_intent_adherence(assigned, generated)
        assert label != ADHERENCE_DRIFTED
        assert should_early_reject_for_intent_drift(label) is False

    def test_same_topic_changed_objective_can_be_true_drift(self):
        from open_notebook.graphs.question_bank_intent import (
            ADHERENCE_DRIFTED,
            classify_intent_adherence,
        )

        # define currency vs distinguish money/currency — different objective
        assigned = self._intent(concept="currency", objective="define currency")
        generated = {
            "question": "What is the main difference between money and currency?",
            "topic": "Currency",
        }
        assert classify_intent_adherence(assigned, generated) == ADHERENCE_DRIFTED

    def test_difficulty_and_answer_type_remain_fixed_for_partial(self):
        from open_notebook.graphs.question_bank_intent import (
            partial_adherence_may_continue,
        )

        assigned = self._intent(
            concept="denominations",
            objective="Identify denominations as different values of money",
        )
        generated = {
            "question": "In India, ₹1, ₹5 and ₹10 are examples of denominations.",
            "topic": "Denominations",
            "target_difficulty": "medium",
            "answer_type": "multiple_correct",
        }
        assert (
            partial_adherence_may_continue(
                assigned,
                generated,
                target_difficulty="easy",
                answer_type="single_correct",
            )
            is False
        )

    def test_downstream_validators_remain_mandatory(self):
        import open_notebook.graphs.question_paper as qp_mod

        fill_src = inspect.getsource(qp_mod.fill_slots)
        assert "run_bank_batch_early_gates" in fill_src
        assert fill_src.index("classify_intent_adherence") < fill_src.index(
            "run_bank_batch_early_gates"
        )
        assert "_validate_slot_independently" in fill_src

    def test_catalog_remains_grounded(self):
        from open_notebook.graphs.question_bank_intent import ground_intent_catalog

        chunks = [
            "Currency includes coins and notes. Money is broader than currency.",
            "Barter exchanges goods without money.",
        ]
        raw = [
            self._intent(concept="currency", objective="define currency", chunk_index=0),
            self._intent(
                intent_id="bad",
                concept="photosynthesis",
                objective="explain photosynthesis",
                chunk_index=0,
            ),
        ]
        grounded, discarded = ground_intent_catalog(raw, chunks)
        assert len(grounded) == 1
        assert discarded >= 1

    def test_final_paper_unchanged_by_intent_alignment(self):
        import open_notebook.graphs.question_paper as qp_mod

        fill_src = inspect.getsource(qp_mod.fill_slots)
        # Adherence only when intent_planner_on (bank_batch_mode + flag)
        assert "intent_planner_on and active_intent" in fill_src
        # prepare_blueprint / paper path must not call bank intent catalog builder
        assert "build_or_load_base_intent_catalog" not in inspect.getsource(qp_mod)

    def test_intent_planner_version_v2(self):
        from open_notebook.graphs.question_bank_intent import INTENT_PLANNER_VERSION

        assert INTENT_PLANNER_VERSION == "v2"


class TestBankBatchNovelGenerationStep8:
    """Step 8: novelty brief + delayed intent retirement (Bank Batch only)."""

    def _intent(self, **kwargs):
        from open_notebook.graphs.question_bank_intent import (
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        base = {
            "intent_id": kwargs.get("intent_id", "i1"),
            "topic": kwargs.get("topic", "Currency"),
            "sub_topic": kwargs.get("sub_topic", "Definition"),
            "concept": kwargs.get("concept", "currency"),
            "objective": kwargs.get("objective", "define currency"),
            "cognitive_form": kwargs.get("cognitive_form", "recall a taught fact"),
            "chunk_index": kwargs.get("chunk_index", 0),
        }
        n = normalize_intent_dict(base)
        n["intent_fingerprint"] = planned_intent_fingerprint(n)
        return n

    def test_closest_bank_stems_supplied_as_avoid_guidance(self):
        from open_notebook.graphs.question_bank_intent import (
            format_bank_batch_novelty_brief,
            select_closest_bank_stems_for_intent,
        )

        assigned = self._intent()
        bank = [
            {
                "question": "What does the term currency mean?",
                "topic": "Currency",
            },
            {
                "question": "Which of these is an example of currency?",
                "topic": "Currency",
            },
            {
                "question": "Why do plants need sunlight for photosynthesis?",
                "topic": "Science",
            },
        ]
        closest = select_closest_bank_stems_for_intent(assigned, bank, limit=3)
        assert 1 <= len(closest) <= 3
        assert any("currency" in (c.get("question") or "").lower() for c in closest)
        brief = format_bank_batch_novelty_brief(
            assigned,
            closest_bank=closest,
            rejected_stems=["What is currency called in India?"],
            target_difficulty="easy",
        )
        assert "NOVELTY BRIEF" in brief
        assert "Already covered" in brief
        assert "do NOT paraphrase" in brief
        assert any(
            (c.get("question") or "")[:40] in brief or "currency" in brief.lower()
            for c in closest
        )

    def test_cosmetic_rewording_not_sufficient_novelty(self):
        from open_notebook.graphs.question_bank_intent import (
            format_bank_batch_novelty_brief,
        )

        brief = format_bank_batch_novelty_brief(
            self._intent(),
            closest_bank=[
                {"question": "What does currency mean?", "question_form": "define"}
            ],
            target_difficulty="easy",
        )
        assert "Cosmetic-only changes are NOT enough" in brief
        assert "reordering options" in brief or "lightly rewording" in brief

    def test_same_concept_can_produce_different_valid_objective(self):
        from open_notebook.graphs.question_bank_intent import (
            format_bank_batch_novelty_brief,
            question_task_form,
        )

        brief = format_bank_batch_novelty_brief(
            self._intent(objective="define currency"),
            target_difficulty="easy",
        )
        assert "definition→recognition" in brief or "recognition→example" in brief
        assert question_task_form("What does currency mean?") == "define"
        assert question_task_form(
            "Which of the following is an example of currency?"
        ) == "example"

    def test_duplicate_retry_adds_matched_stem_to_avoid_history(self):
        from open_notebook.graphs.question_bank_intent import (
            duplicate_intent_keep_feedback,
        )

        fb = duplicate_intent_keep_feedback(
            self._intent(),
            dup_match={
                "matched_stem": "What does currency mean in this chapter?",
                "matched_intent_fingerprint": "concept currency define",
            },
        )
        assert "Add to avoid list" in fb
        assert "What does currency mean" in fb
        assert "SAME assigned intent" in fb

    def test_first_duplicate_does_not_automatically_retire_valid_intent(self):
        from open_notebook.graphs.question_bank_intent import (
            apply_duplicate_intent_policy,
            empty_intent_diagnostics,
        )

        assigned = self._intent(intent_id="keep-me")
        hits: dict = {}
        retired: set = set()
        remaining = [
            self._intent(intent_id="next", objective="identify barter", concept="barter")
        ]
        assignments = {"1": assigned}
        diag = empty_intent_diagnostics()
        nxt, extra, retired_flag = apply_duplicate_intent_policy(
            active_intent=assigned,
            intent_dup_hits=hits,
            intent_retired_ids=retired,
            intent_remaining=remaining,
            intent_assignments=assignments,
            slot_key="1",
            intent_diagnostics=diag,
            dup_match={"matched_stem": "Old stem about currency"},
        )
        assert retired_flag is False
        assert nxt is assigned
        assert "keep-me" not in retired
        assert diag["duplicate_retry_same_intent"] == 1
        assert diag["intents_retired_after_duplicate"] == 0
        assert "INTENT NOVELTY RETRY" in extra
        assert remaining  # not consumed yet

    def test_repeated_duplicate_can_retire_intent(self):
        from open_notebook.graphs.question_bank_intent import (
            apply_duplicate_intent_policy,
            empty_intent_diagnostics,
        )

        assigned = self._intent(intent_id="old")
        hits = {"old": 1}  # already one hit
        retired: set = set()
        remaining = [
            self._intent(intent_id="next", objective="identify barter", concept="barter")
        ]
        assignments = {"1": assigned}
        diag = empty_intent_diagnostics()
        nxt, extra, retired_flag = apply_duplicate_intent_policy(
            active_intent=assigned,
            intent_dup_hits=hits,
            intent_retired_ids=retired,
            intent_remaining=remaining,
            intent_assignments=assignments,
            slot_key="1",
            intent_diagnostics=diag,
        )
        assert retired_flag is True
        assert "old" in retired
        assert nxt is not None and nxt["intent_id"] == "next"
        assert diag["intents_retired_after_repeated_duplicates"] == 1
        assert diag["intents_retired_after_duplicate"] == 1
        assert remaining == []

    def test_difficulty_and_answer_type_stay_fixed(self):
        from open_notebook.graphs.question_bank_intent import (
            format_bank_batch_novelty_brief,
        )
        import open_notebook.graphs.question_paper as qp_mod

        brief = format_bank_batch_novelty_brief(
            self._intent(), target_difficulty="easy"
        )
        assert "target_difficulty: easy" in brief
        assert "do not raise cognitive level" in brief
        gen_src = inspect.getsource(qp_mod._generate_for_slot)
        assert "keeping the SAME" in gen_src
        assert "chapter, target difficulty, and answer type" in gen_src

    def test_final_paper_unchanged_by_novelty_brief(self):
        import open_notebook.graphs.question_paper as qp_mod

        gen_src = inspect.getsource(qp_mod._generate_for_slot)
        assert "bank_batch_mode and novelty_brief" in gen_src.replace("\n", " ")
        fill_src = inspect.getsource(qp_mod.fill_slots)
        assert "format_bank_batch_novelty_brief" in fill_src
        assert "apply_duplicate_intent_policy" in fill_src
        # Final Paper path must not build intent catalogs
        assert "build_or_load_base_intent_catalog" not in inspect.getsource(qp_mod)


class TestBankBatchIntentReplenishmentStep9:
    """Step 9: expandable intent catalog + chunk replenishment (Bank Batch only)."""

    def _chunks(self):
        return [
            "Currency includes coins, paper notes, and digital money. Money is a broader concept.",
            "Barter is direct exchange of goods without money. Double coincidence of wants is a problem.",
            "Banks accept deposits and give loans. Savings accounts help people store money safely.",
        ]

    def _intent(self, **kwargs):
        return TestBankBatchIntentPlannerStep7()._intent(**kwargs)

    def test_cache_hit_is_not_sufficient_for_50q(self):
        from open_notebook.graphs.question_bank_intent import should_replenish_catalog

        assert should_replenish_catalog(
            unused_intents=26,
            missing_slots=50,
            catalog_size=26,
            requested_count=50,
            planner_calls=0,
            replenish_rounds=0,
            require_capacity_for_missing=True,
        )
        assert not should_replenish_catalog(
            unused_intents=26,
            missing_slots=20,
            catalog_size=26,
            requested_count=20,
            planner_calls=0,
            replenish_rounds=0,
            require_capacity_for_missing=True,
        )

    def test_fill_time_uses_unused_threshold_not_missing_slots(self):
        from open_notebook.graphs.question_bank_intent import should_replenish_catalog

        assert not should_replenish_catalog(
            unused_intents=6,
            missing_slots=20,
            catalog_size=26,
            requested_count=20,
            planner_calls=0,
            replenish_rounds=0,
            require_capacity_for_missing=False,
        )
        assert should_replenish_catalog(
            unused_intents=4,
            missing_slots=20,
            catalog_size=26,
            requested_count=20,
            planner_calls=0,
            replenish_rounds=0,
            require_capacity_for_missing=False,
        )

    def test_undercovered_chunks_are_preferred(self):
        from open_notebook.graphs.question_bank_intent import (
            select_undercovered_chunk_indices,
        )

        catalog = [
            self._intent(chunk_index=0, intent_id="a"),
            self._intent(chunk_index=0, intent_id="b", objective="identify coins"),
        ]
        ranked = select_undercovered_chunk_indices(catalog, self._chunks())
        assert ranked[0] != 0
        assert ranked[0] in (1, 2)

    def test_duplicate_replenished_intent_not_merged(self):
        from open_notebook.graphs.question_bank_intent import merge_grounded_catalog

        existing = [self._intent(intent_id="keep")]
        dup = self._intent(
            intent_id="new-dup",
            objective="define currency",
            concept="currency",
        )
        novel = self._intent(
            intent_id="novel",
            concept="barter",
            objective="identify double coincidence of wants",
            chunk_index=1,
        )
        merged, removed = merge_grounded_catalog(existing, [dup, novel])
        ids = {x["intent_id"] for x in merged}
        assert "keep" in ids
        assert "novel" in ids
        assert "new-dup" not in ids
        assert removed >= 1

    def test_grounding_rejects_unsupported_replenish_intent(self):
        from open_notebook.graphs.question_bank_intent import ground_intent_catalog

        hallucinated = self._intent(
            concept="photosynthesis",
            objective="explain chlorophyll absorbing sunlight",
            chunk_index=0,
        )
        grounded, discarded = ground_intent_catalog([hallucinated], self._chunks())
        assert grounded == []
        assert discarded >= 1

    def test_planner_and_round_limits_stop_replenish(self):
        from open_notebook.graphs.question_bank_intent import (
            INTENT_MAX_PLANNER_CALLS_PER_BATCH,
            INTENT_MAX_REPLENISH_ROUNDS,
            should_replenish_catalog,
        )

        assert not should_replenish_catalog(
            unused_intents=0,
            missing_slots=20,
            catalog_size=10,
            requested_count=20,
            planner_calls=INTENT_MAX_PLANNER_CALLS_PER_BATCH,
            replenish_rounds=0,
            require_capacity_for_missing=True,
        )
        assert not should_replenish_catalog(
            unused_intents=0,
            missing_slots=20,
            catalog_size=10,
            requested_count=20,
            planner_calls=0,
            replenish_rounds=INTENT_MAX_REPLENISH_ROUNDS,
            require_capacity_for_missing=True,
        )

    def test_hard_cap_blocks_further_expansion(self):
        from open_notebook.graphs.question_bank_intent import (
            catalog_hard_cap,
            should_replenish_catalog,
        )

        requested = 20
        hard = catalog_hard_cap(requested)
        assert hard == 40
        assert not should_replenish_catalog(
            unused_intents=0,
            missing_slots=20,
            catalog_size=hard,
            requested_count=requested,
            planner_calls=0,
            replenish_rounds=0,
            require_capacity_for_missing=True,
        )

    @pytest.mark.asyncio
    async def test_expand_preserves_cached_intents_and_grows(self, monkeypatch):
        from open_notebook.graphs import question_bank_intent as qbi

        chunks = self._chunks()
        cached = [
            self._intent(intent_id="cached-1", chunk_index=0),
            self._intent(
                intent_id="cached-2",
                concept="currency",
                objective="distinguish currency from money",
                chunk_index=0,
            ),
        ]
        calls = {"n": 0}

        async def fake_llm(**kwargs):
            calls["n"] += 1
            idx = int(kwargs.get("chunk_index") or 0)
            if idx == 1:
                return [
                    self._intent(
                        intent_id=f"new-barter-{calls['n']}",
                        concept="barter",
                        topic="Barter",
                        objective="identify that barter needs double coincidence of wants",
                        chunk_index=1,
                    )
                ]
            return [
                self._intent(
                    intent_id=f"new-bank-{calls['n']}",
                    concept="banks",
                    topic="Banks",
                    objective="recall that banks accept deposits and give loans",
                    chunk_index=2,
                )
            ]

        monkeypatch.setattr(qbi, "generate_replenish_intents_via_llm", fake_llm)
        diag = qbi.empty_intent_diagnostics()
        expanded = await qbi.expand_intent_catalog_for_request(
            catalog=cached,
            chunks=chunks,
            requested_count=20,
            missing_slots=20,
            unused_intents=2,
            grade="5",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Money",
            difficulty="easy",
            diagnostics=diag,
            require_capacity_for_missing=True,
        )
        ids = [x["intent_id"] for x in expanded]
        assert "cached-1" in ids
        assert "cached-2" in ids
        assert len(expanded) > len(cached)
        assert 1 <= calls["n"] <= qbi.INTENT_MAX_PLANNER_CALLS_PER_BATCH
        assert diag["replenishment_rounds"] <= qbi.INTENT_MAX_REPLENISH_ROUNDS

    @pytest.mark.asyncio
    async def test_no_infinite_replenishment_when_llm_adds_nothing(self, monkeypatch):
        from open_notebook.graphs import question_bank_intent as qbi

        async def fake_llm(**kwargs):
            return [
                self._intent(
                    intent_id="dup-again",
                    objective="define currency",
                    concept="currency",
                    chunk_index=0,
                )
            ]

        monkeypatch.setattr(qbi, "generate_replenish_intents_via_llm", fake_llm)
        catalog = [self._intent(intent_id="orig")]
        expanded = await qbi.expand_intent_catalog_for_request(
            catalog=catalog,
            chunks=self._chunks(),
            requested_count=50,
            missing_slots=50,
            unused_intents=1,
            grade="5",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Money",
            difficulty="easy",
            require_capacity_for_missing=True,
        )
        assert len(expanded) == 1
        assert expanded[0]["intent_id"] == "orig"

    @pytest.mark.asyncio
    async def test_hard_cap_respected_during_merge(self, monkeypatch):
        from open_notebook.graphs import question_bank_intent as qbi

        requested = 8
        hard = qbi.catalog_hard_cap(requested)
        catalog = [
            self._intent(
                intent_id=f"c{i}",
                objective=f"recall unique currency fact number {i} about coins",
                concept=f"currency-{i}",
                chunk_index=0,
            )
            for i in range(hard - 1)
        ]

        async def fake_llm(**kwargs):
            return [
                self._intent(
                    intent_id=f"extra-{i}",
                    concept="barter",
                    objective=f"identify barter problem variant {i}",
                    chunk_index=1,
                )
                for i in range(12)
            ]

        monkeypatch.setattr(qbi, "generate_replenish_intents_via_llm", fake_llm)
        expanded = await qbi.expand_intent_catalog_for_request(
            catalog=catalog,
            chunks=self._chunks(),
            requested_count=requested,
            missing_slots=requested,
            unused_intents=2,
            grade="5",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Money",
            difficulty="easy",
            require_capacity_for_missing=True,
        )
        assert len(expanded) <= hard

    @pytest.mark.asyncio
    async def test_same_cache_key_expands_in_place(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as qbi

        monkeypatch.setattr(qbi, "_cache_dir", lambda: tmp_path)
        key = qbi.intent_cache_key(
            book_id="book:x",
            chapter=1,
            difficulty="easy",
            content_hash="abc123abc123abc123abc123",
        )
        small = [self._intent(intent_id="seed")]
        qbi.save_cached_intent_catalog(
            key,
            small,
            meta={"requested_count": 20, "catalog_version": qbi.INTENT_CATALOG_SCHEMA_VERSION},
        )
        loaded = qbi.load_cached_intent_catalog(key)
        assert loaded and loaded[0]["intent_id"] == "seed"

        async def fake_llm(**kwargs):
            return [
                self._intent(
                    intent_id="expanded-barter",
                    concept="barter",
                    topic="Barter",
                    objective="identify double coincidence of wants in barter",
                    chunk_index=1,
                )
            ]

        monkeypatch.setattr(qbi, "generate_replenish_intents_via_llm", fake_llm)
        grown = await qbi.expand_intent_catalog_for_request(
            catalog=list(loaded),
            chunks=self._chunks(),
            requested_count=50,
            missing_slots=50,
            unused_intents=1,
            grade="5",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Money",
            difficulty="easy",
            cache_key=key,
            require_capacity_for_missing=True,
        )
        assert len(grown) > 1
        reloaded = qbi.load_cached_intent_catalog(key)
        ids = {x["intent_id"] for x in (reloaded or [])}
        assert "seed" in ids
        rec = qbi.load_intent_catalog_record(key)
        assert rec["meta"]["total_catalog_intents"] == len(reloaded)
        assert rec["meta"]["catalog_version"] == qbi.INTENT_CATALOG_SCHEMA_VERSION

    def test_replenish_prompt_asks_for_new_objectives_not_paraphrase(self):
        from open_notebook.graphs.question_bank_intent import build_replenish_prompts

        system, user = build_replenish_prompts(
            grade="5",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Money",
            difficulty="easy",
            chunk_index=1,
            chunk_text=self._chunks()[1],
            batch_size=10,
            avoid_objectives=["currency: define currency"],
            heavy_topics=["currency"],
        )
        blob = f"{system}\n{user}".lower()
        assert "paraphrase" in blob
        assert "chunk_index" in user
        assert "define currency" in user

    def test_final_paper_unchanged_by_step9_replenishment(self):
        import open_notebook.graphs.question_paper as qp_mod
        from open_notebook.graphs import question_bank_batch as qbb

        assert "expand_intent_catalog_for_request" in inspect.getsource(
            qbb.prepare_bank_batch
        )
        fill_src = inspect.getsource(qp_mod.fill_slots)
        assert "replenish_running_pool" in fill_src
        assert "intent_planner_on" in fill_src
        assert "build_or_load_base_intent_catalog" not in inspect.getsource(qp_mod)
        gen_src = inspect.getsource(qp_mod._generate_for_slot)
        assert "bank_batch_mode and intent_guidance" in gen_src.replace("\n", " ")


class TestBankBatchTokenContextOptimization:
    def test_grounding_window_is_800_to_1500_not_full_chunk(self):
        from open_notebook.graphs.question_paper_blueprint import (
            select_source_grounding_window,
        )

        chunk = ("alpha " * 200) + ("currency barter money functions " * 40) + ("omega " * 200)
        assert len(chunk) > 1500
        window = select_source_grounding_window(chunk, "currency barter money")
        assert 800 <= len(window) <= 1500
        assert "currency" in window.lower()

    def test_blind_snippet_omits_unrelated_full_chunk(self):
        from open_notebook.graphs.question_paper_blueprint import (
            select_blind_solver_source_snippet,
        )

        chunk = "zzz " * 1000
        snippet = select_blind_solver_source_snippet(
            chunk, "What is 2 + 2?", ["1", "2", "3", "4", "5"]
        )
        assert snippet == ""

    def test_blind_snippet_is_small_when_terms_match(self):
        from open_notebook.graphs.question_paper_blueprint import (
            select_blind_solver_source_snippet,
        )

        chunk = ("padding " * 400) + "legal tender currency notes coins " + ("tail " * 400)
        snippet = select_blind_solver_source_snippet(
            chunk,
            "Which item is legal tender currency?",
            ["notes", "barter", "gold", "credit", "cheque"],
        )
        assert snippet
        assert len(snippet) <= 700
        assert "tender" in snippet.lower() or "currency" in snippet.lower()

    def test_forbidden_stems_capped_8_to_12_closest(self):
        from open_notebook.graphs.question_paper_blueprint import (
            select_bank_batch_forbidden_stems,
        )

        used = [f"Unrelated stem number {i} about vegetables?" for i in range(30)]
        used.append("What is the main function of currency as a medium of exchange?")
        picked = select_bank_batch_forbidden_stems(
            {"concept": "currency", "objective": "identify functions of money"},
            used_stems=used,
            rejected_stems=["Define currency in one sentence."],
            existing_questions=[{"question": "How does money act as a store of value?"}],
            limit=10,
        )
        assert 8 <= len(picked) <= 12
        blob = " ".join(picked).lower()
        assert "currency" in blob or "money" in blob

    def test_bank_batch_only_reduces_validator_and_blind_context(self):
        import open_notebook.graphs.question_paper as qp_mod

        blind_src = inspect.getsource(qp_mod._blind_solve)
        cog_src = inspect.getsource(qp_mod._validate_cognitive_quality)
        gen_src = inspect.getsource(qp_mod._generate_for_slot)
        assert "select_blind_solver_source_snippet" in blind_src
        assert "bank_batch_mode" in blind_src
        assert "select_source_grounding_window" in cog_src
        assert "forbidden_stems" in gen_src
        paper_src = inspect.getsource(qp_mod.build_question_paper_graph)
        assert "bank_target_refill" not in paper_src
        assert "select_blind_solver_source_snippet" not in paper_src

    def test_final_paper_still_uses_last_40_stems_by_default(self):
        import open_notebook.graphs.question_paper as qp_mod

        gen_src = inspect.getsource(qp_mod._generate_for_slot)
        assert "forbidden[-40:]" in gen_src.replace(" ", "")
        assert "forbidden_stems is not None" in gen_src


def _capture_generate_prompts():
    captured = {}

    async def fake_invoke(system, user_prompt, *args, **kwargs):
        captured["system"] = system
        captured["user"] = user_prompt

        class R:
            def model_dump(self):
                return {
                    "question": "What is X?",
                    "topic": "Money",
                    "sub_topic": "Coins",
                    "options": ["A", "B", "C", "D", "E"],
                    "correct_indices": [0],
                    "answer": "A",
                    "explanation": "Because.",
                }

        return R()

    return captured, fake_invoke


class TestBankBatchEasyGenerationCalibration:
    def test_easy_calibration_not_in_shared_generator_or_validator(self):
        assert "EASY CALIBRATION" not in qp.GENERATOR_SYSTEM
        assert "BANK BATCH EASY CALIBRATION" not in qp.GENERATOR_SYSTEM
        assert "EASY CALIBRATION" not in qp.VALIDATOR_SYSTEM
        assert "BANK BATCH EASY CALIBRATION" not in qp.BLIND_SOLVER_SYSTEM

    def test_cognitive_map_thresholds_unchanged(self):
        from open_notebook.graphs.question_paper_blueprint import map_cognitive_score

        assert map_cognitive_score(8) == "easy"
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        assert map_cognitive_score(24) == "difficult"

    def test_easy_rules_require_one_concept_and_forbid_evaluation(self):
        rules = qp.BANK_BATCH_EASY_CALIBRATION_RULES.lower()
        assert "one primary concept" in rules
        assert "0–1" in qp.BANK_BATCH_EASY_CALIBRATION_RULES or "0-1" in rules
        assert "best decision" in rules
        assert "multi-step" in rules
        assert "plausible" in rules

    @pytest.mark.asyncio
    async def test_bank_batch_easy_prompt_includes_calibration(self):
        captured, fake_invoke = _capture_generate_prompts()
        slot = QuestionSlot(
            question_number=1,
            chapter=2,
            chapter_title="Chapter 2",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="9",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": True, "book_grounded": True, "language": "en"},
                "banks and transfers",
                None,
            )
        assert "BANK BATCH EASY CALIBRATION" in captured["system"]
        assert "EASY CALIBRATION (Bank Batch)" in captured["user"]
        assert "0–1 reasoning step" in captured["user"]
        assert "best-decision" in captured["user"]

    @pytest.mark.asyncio
    async def test_bank_batch_medium_prompt_omits_easy_calibration(self):
        captured, fake_invoke = _capture_generate_prompts()
        slot = QuestionSlot(
            question_number=2,
            chapter=2,
            chapter_title="Chapter 2",
            target_difficulty="medium",
            answer_type="single_correct",
            grade="9",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": True, "book_grounded": True, "language": "en"},
                "banks and transfers",
                None,
            )
        assert "BANK BATCH EASY CALIBRATION" not in captured["system"]
        assert "EASY CALIBRATION (Bank Batch)" not in captured["user"]

    @pytest.mark.asyncio
    async def test_bank_batch_difficult_prompt_omits_easy_calibration(self):
        captured, fake_invoke = _capture_generate_prompts()
        slot = QuestionSlot(
            question_number=3,
            chapter=2,
            chapter_title="Chapter 2",
            target_difficulty="difficult",
            answer_type="single_correct",
            grade="9",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": True, "book_grounded": True, "language": "en"},
                "banks and transfers",
                None,
            )
        assert "BANK BATCH EASY CALIBRATION" not in captured["system"]
        assert "EASY CALIBRATION (Bank Batch)" not in captured["user"]

    @pytest.mark.asyncio
    async def test_final_paper_easy_prompt_omits_easy_calibration(self):
        captured, fake_invoke = _capture_generate_prompts()
        slot = QuestionSlot(
            question_number=1,
            chapter=2,
            chapter_title="Chapter 2",
            target_difficulty="easy",
            answer_type="single_correct",
            grade="9",
            subject="Financial Literacy",
        )
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {"bank_batch_mode": False, "book_grounded": True, "language": "en"},
                "banks and transfers",
                None,
            )
        assert "BANK BATCH EASY CALIBRATION" not in captured["system"]
        assert "EASY CALIBRATION (Bank Batch)" not in captured["user"]


class TestBankBatchEasyIntentGuard:
    def test_cognitive_thresholds_unchanged(self):
        from open_notebook.graphs.question_paper_blueprint import map_cognitive_score

        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"

    def test_easy_safe_accepts_recall_and_rejects_medium_objectives(self):
        from open_notebook.graphs.question_bank_intent import intent_is_easy_safe

        assert intent_is_easy_safe(
            {
                "cognitive_form": "recall a taught fact",
                "concept": "REITs",
                "objective": "Recall that REITs are companies that own real estate portfolios",
            }
        )
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "identify a concept",
                "concept": "Interest rate risk",
                "objective": "Identify how changes in interest rates affect bond prices",
            }
        )
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "distinguish two taught concepts",
                "concept": "Investment",
                "objective": "Define investing and distinguish it from saving in terms of risk",
            }
        )
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "identify a concept",
                "concept": "EMI",
                "objective": "Identify EMI as a payment that includes both principal and interest",
            }
        )
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "compare related taught concepts",
                "concept": "Bonds",
                "objective": "Compare bond risk with stock risk in a scenario",
            }
        )

    def test_medium_intents_not_filtered_by_easy_guard(self):
        from open_notebook.graphs.question_bank_intent import filter_easy_safe_intents

        medium = [
            {
                "intent_id": "m1",
                "cognitive_form": "compare related taught concepts",
                "concept": "Bonds",
                "objective": "Compare bond risk with stock risk",
            }
        ]
        kept = filter_easy_safe_intents(medium, difficulty="medium")
        assert len(kept) == 1

    def test_take_next_skips_unsafe_easy_intents(self):
        from open_notebook.graphs.question_bank_intent import take_next_unused_intent

        remaining = [
            {
                "intent_id": "bad",
                "cognitive_form": "identify a concept",
                "concept": "Diversification",
                "objective": "Identify how diversification protects value when one asset underperforms",
            },
            {
                "intent_id": "good",
                "cognitive_form": "recall a taught fact",
                "concept": "REITs",
                "objective": "Recall that REITs own and operate real estate portfolios",
            },
        ]
        diag = {}
        nxt = take_next_unused_intent(
            remaining, target_difficulty="easy", diagnostics=diag
        )
        assert nxt["intent_id"] == "good"
        assert int(diag.get("easy_intents_skipped_unsafe") or 0) >= 1

    def test_easy_planner_prompt_includes_easy_intent_rules_only(self):
        from open_notebook.graphs.question_bank_intent import build_intent_planner_prompts

        sys_e, user_e = build_intent_planner_prompts(
            grade="9",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Ch1",
            difficulty="easy",
            requested_count=20,
            chunks=["Currency is money in use."],
        )
        sys_m, user_m = build_intent_planner_prompts(
            grade="9",
            subject="Financial Literacy",
            chapter=1,
            chapter_title="Ch1",
            difficulty="medium",
            requested_count=20,
            chunks=["Currency is money in use."],
        )
        assert "EASY INTENT RULES" in sys_e
        assert "distinguish two taught concepts" not in user_e
        assert "direct comprehension" in user_e
        assert "EASY INTENT RULES" not in sys_m
        assert "compare related taught concepts" in user_m

    def test_final_paper_graph_does_not_import_easy_intent_rules_into_validator(self):
        import open_notebook.graphs.question_paper as qp_mod

        assert "EASY INTENT RULES" not in qp_mod.VALIDATOR_SYSTEM
        assert "EASY INTENT RULES" not in qp_mod.GENERATOR_SYSTEM

    def test_top_up_passes_slot_difficulty_not_bare_slot(self):
        import inspect
        import open_notebook.graphs.question_paper as qp_mod

        fill_src = inspect.getsource(qp_mod.fill_slots)
        assert "target_difficulty=slot.target_difficulty" in fill_src
        assert "async def _top_up_intents(" in fill_src
        assert "*," in fill_src


class TestIntentCatalogCacheFailureNotReused:
    """Failed/empty planner caches must not be reused as valid catalogs."""

    def _chunks(self):
        return [
            "Currency includes coins, paper notes, and digital money. Money is a broader concept.",
            "Barter is direct exchange of goods without money. Double coincidence of wants is a problem.",
        ]

    def _intent(self, **kwargs):
        from open_notebook.graphs.question_bank_intent import (
            normalize_intent_dict,
            planned_intent_fingerprint,
        )

        base = {
            "intent_id": kwargs.get("intent_id", "i1"),
            "topic": kwargs.get("topic", "Currency"),
            "sub_topic": kwargs.get("sub_topic", "Definition"),
            "concept": kwargs.get("concept", "currency"),
            "objective": kwargs.get("objective", "define currency"),
            "cognitive_form": kwargs.get("cognitive_form", "recall a taught fact"),
            "source_section": kwargs.get("source_section", "Currency"),
            "chunk_index": kwargs.get("chunk_index", 0),
        }
        n = normalize_intent_dict(base)
        n["intent_fingerprint"] = planned_intent_fingerprint(n)
        return n

    def _chapter_text(self):
        return "Currency includes coins, paper notes, and digital money."

    def _key(self, ib):
        return ib.intent_cache_key(
            book_id="book:cache-test",
            chapter=1,
            difficulty="easy",
            content_hash=ib.chapter_content_hash(self._chapter_text()),
        )

    def test_failed_planner_result_is_not_reused(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        key = self._key(ib)
        ib.save_cached_intent_catalog(
            key,
            [],
            meta={"status": ib.INTENT_CATALOG_STATUS_FAILED, "error": "provider 400"},
        )
        rec = ib.load_intent_catalog_record(key)
        assert rec is not None
        assert ib.intent_catalog_record_status(rec) == ib.INTENT_CATALOG_STATUS_FAILED
        assert ib.load_cached_intent_catalog(key) is None
        assert ib.is_reusable_intent_catalog_record(rec) is False

    def test_zero_grounded_legacy_empty_file_not_reused(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        key = self._key(ib)
        path = ib._cache_file(key)
        path.write_text(
            json.dumps(
                {
                    "planner_version": ib.INTENT_PLANNER_VERSION,
                    "cache_key": key,
                    "intents": [],
                    "meta": {"grounded_count": 0, "total_catalog_intents": 0},
                }
            ),
            encoding="utf-8",
        )
        assert ib.load_cached_intent_catalog(key) is None

    def test_valid_non_empty_catalog_is_reused(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        key = self._key(ib)
        intents = [self._intent()]
        ib.save_cached_intent_catalog(key, intents)
        loaded = ib.load_cached_intent_catalog(key)
        assert loaded is not None
        assert len(loaded) == 1
        rec = ib.load_intent_catalog_record(key)
        assert rec["meta"]["status"] == ib.INTENT_CATALOG_STATUS_COMPLETE

    @pytest.mark.asyncio
    async def test_provider_failure_does_not_poison_next_rebuild(
        self, tmp_path, monkeypatch
    ):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        calls = {"n": 0}

        async def fail_then_ok(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("API usage limits")
            return [self._intent()]

        monkeypatch.setattr(ib, "generate_intent_catalog_via_llm", fail_then_ok)
        kwargs = dict(
            book_id="book:cache-test",
            chapter=1,
            difficulty="easy",
            chapter_text=self._chapter_text(),
            chunks=self._chunks(),
            grade="6",
            subject="Financial Literacy",
            chapter_title="Chapter 1",
            requested_count=20,
        )
        diag1 = ib.empty_intent_diagnostics()
        first = await ib.build_or_load_base_intent_catalog(
            **kwargs, diagnostics=diag1
        )
        assert first == []
        assert diag1["cache_hit"] is False
        rec = ib.load_intent_catalog_record(self._key(ib))
        assert rec["meta"]["status"] == ib.INTENT_CATALOG_STATUS_FAILED
        assert ib.load_cached_intent_catalog(self._key(ib)) is None

        diag2 = ib.empty_intent_diagnostics()
        second = await ib.build_or_load_base_intent_catalog(
            **kwargs, diagnostics=diag2
        )
        assert len(second) >= 1
        assert diag2["cache_hit"] is False
        assert calls["n"] == 2
        assert ib.load_cached_intent_catalog(self._key(ib)) is not None

        diag3 = ib.empty_intent_diagnostics()
        third = await ib.build_or_load_base_intent_catalog(
            **kwargs, diagnostics=diag3
        )
        assert len(third) >= 1
        assert diag3["cache_hit"] is True
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_zero_grounded_from_empty_llm_not_reused(
        self, tmp_path, monkeypatch
    ):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        calls = {"n": 0}

        async def empty_then_ok(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return []
            return [self._intent()]

        monkeypatch.setattr(ib, "generate_intent_catalog_via_llm", empty_then_ok)
        kwargs = dict(
            book_id="book:cache-test",
            chapter=1,
            difficulty="easy",
            chapter_text=self._chapter_text(),
            chunks=self._chunks(),
            grade="6",
            subject="Financial Literacy",
            chapter_title="Chapter 1",
            requested_count=20,
        )
        await ib.build_or_load_base_intent_catalog(**kwargs)
        assert ib.load_cached_intent_catalog(self._key(ib)) is None
        rebuilt = await ib.build_or_load_base_intent_catalog(**kwargs)
        assert len(rebuilt) >= 1
        assert calls["n"] == 2

    def test_partial_status_not_reused(self, tmp_path, monkeypatch):
        from open_notebook.graphs import question_bank_intent as ib

        monkeypatch.setattr(ib, "_cache_dir", lambda: tmp_path)
        key = self._key(ib)
        ib.save_cached_intent_catalog(
            key,
            [],
            meta={"status": ib.INTENT_CATALOG_STATUS_PARTIAL},
        )
        assert ib.load_cached_intent_catalog(key) is None

    def test_final_paper_still_does_not_use_intent_catalog_cache(self):
        import open_notebook.graphs.question_paper as qp_mod

        paper_src = inspect.getsource(qp_mod)
        assert "build_or_load_base_intent_catalog" not in paper_src
        assert "load_cached_intent_catalog" not in paper_src



