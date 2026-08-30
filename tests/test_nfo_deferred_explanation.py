"""Offline tests: Bank Batch deferred explanation (core first, then explanation)."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    empty_bank_cost_diagnostics,
    finalize_bank_cost_diagnostics,
    map_cognitive_score,
)


def _slot(**overrides) -> QuestionSlot:
    base = dict(
        question_number=1,
        chapter=1,
        chapter_title="Money",
        target_difficulty="easy",
        answer_type="single_correct",
        grade="5",
        subject="Financial Literacy",
    )
    base.update(overrides)
    return QuestionSlot(**base)


def _core(**overrides) -> dict:
    data = {
        "question": "What is barter?",
        "topic": "Barter",
        "sub_topic": "Exchange",
        "options": [
            "Exchange of goods without money",
            "A bank loan",
            "A tax paid yearly",
            "Digital payment only",
            "A government salary",
        ],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "",
    }
    data.update(overrides)
    return data


def _scores(level: int = 1) -> dict:
    return {c: level for c in qp.COGNITIVE_CRITERIA}


def _flags_ok(*, include_explanation: bool = False) -> dict:
    flags = {
        "content_valid": True,
        "answer_valid": True,
        "grade_appropriate": True,
        "distractors_ok": True,
        "unambiguous": True,
        "language_clear": True,
        "grounded_in_material": True,
        "concept_relevant": True,
        "no_unrelated_external_knowledge": True,
        "stem_self_contained": True,
        "natural_assessment_wording": True,
        "scenario_focused": True,
        "options_independently_assessable": True,
        "option_style_balanced": True,
        "misconception_based_distractors": True,
        "reasons": [],
    }
    if include_explanation:
        flags["explanation_valid"] = True
    return flags


def _blind_ok():
    class _R:
        def model_dump(self):
            return {
                "independently_derived_indices": [0],
                "information_sufficient": True,
                "arithmetic_consistent": True,
                "no_unsupported_claims": True,
                "terminology_grounded": True,
                "option_analysis": [
                    {"option": "A", "defensible": True, "reason": "ok"},
                    {"option": "B", "defensible": False, "reason": "no"},
                    {"option": "C", "defensible": False, "reason": "no"},
                    {"option": "D", "defensible": False, "reason": "no"},
                    {"option": "E", "defensible": False, "reason": "no"},
                ],
            }

    return _R()


def _blind_disagree():
    class _R:
        def model_dump(self):
            return {
                "independently_derived_indices": [1],
                "information_sufficient": True,
                "arithmetic_consistent": True,
                "no_unsupported_claims": True,
                "terminology_grounded": True,
                "option_analysis": [],
            }

    return _R()


class TestCoreSchemaAndConstants:
    def test_core_schema_has_no_explanation_field(self):
        fields = qp.CoreGeneratedQuestion.model_fields
        assert "explanation" not in fields
        assert "question" in fields
        assert "options" in fields
        assert "correct_indices" in fields

    def test_final_paper_schema_still_requires_explanation(self):
        assert "explanation" in qp.SlotGeneratedQuestion.model_fields

    def test_max_explanation_attempts_is_two(self):
        # Initial + one corrective retry
        assert qp.MAX_EXPLANATION_ATTEMPTS == 2

    def test_attempt_limits_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_cognitive_thresholds_unchanged(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"


class TestCoreValidationSkipsExplanationFlag:
    def test_require_explanation_valid_false_ignores_missing_flag(self):
        slot = _slot()
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=_scores(1),
            quality_flags=_flags_ok(include_explanation=False),
            question=_core(),
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_blind_ok().model_dump(),
            require_explanation_valid=False,
        )
        assert result["passed"] is True
        assert not any("explanation" in r.lower() for r in result["validation_reasons"])

    def test_final_paper_still_requires_explanation_valid(self):
        slot = _slot()
        flags = _flags_ok(include_explanation=False)
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=_scores(1),
            quality_flags=flags,
            question={**_core(), "explanation": "Because barter is exchange."},
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_blind_ok().model_dump(),
            require_explanation_valid=True,
        )
        assert result["passed"] is False
        assert any("explanation is invalid" in r for r in result["validation_reasons"])

    def test_cognitive_score_identical_without_explanation(self):
        slot = _slot()
        scores = _scores(1)
        a = apply_independent_validation(
            slot=slot,
            criterion_scores=scores,
            quality_flags=_flags_ok(include_explanation=False),
            question=_core(),
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_blind_ok().model_dump(),
            require_explanation_valid=False,
        )
        b = apply_independent_validation(
            slot=slot,
            criterion_scores=scores,
            quality_flags=_flags_ok(include_explanation=True),
            question={**_core(), "explanation": "Because barter is exchange without money."},
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_blind_ok().model_dump(),
            require_explanation_valid=True,
        )
        assert a["difficulty_score"] == b["difficulty_score"] == 8
        assert a["validated_cognitive_difficulty"] == b["validated_cognitive_difficulty"]


class TestDeferredExplanationPipeline:
    @pytest.fixture(autouse=True)
    def _disable_intent_planner(self, monkeypatch):
        monkeypatch.setenv("QUESTION_BANK_INTENT_PLANNER", "0")
        monkeypatch.setenv("QUESTION_BANK_DIVERSITY_PLANNER", "0")

    @pytest.mark.asyncio
    async def test_structural_fail_no_explanation_call(self):
        slot = _slot()
        generated = _core()
        generated["options"] = generated["options"][:4]
        expl = AsyncMock(return_value=(True, generated, []))

        async def fake_gen(*_a, **_k):
            return generated

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(qp, "_generate_for_slot", side_effect=fake_gen), patch.object(
            qp, "_finalize_bank_batch_explanation", expl
        ), patch.object(
            qp, "_blind_solve", side_effect=AssertionError("no blind")
        ), patch.object(
            qp, "_validate_cognitive_quality", side_effect=AssertionError("no cog")
        ):
            result = await qp.fill_slots(state)

        expl.assert_not_called()
        cost = result.get("cost_diagnostics") or {}
        assert cost.get("explanations_avoided_core_failed", 0) >= 1
        assert cost.get("explanation_generation_calls", 0) == 0
        assert result.get("approved") == []

    @pytest.mark.asyncio
    async def test_early_duplicate_no_explanation_call(self):
        slot = _slot()
        seed = "What is barter?"
        generated = _core(question=seed)
        expl = AsyncMock()

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
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_finalize_bank_batch_explanation", expl), patch.object(
            qp, "_blind_solve", side_effect=AssertionError("no blind")
        ), patch.object(
            qp, "_validate_cognitive_quality", side_effect=AssertionError("no cog")
        ):
            result = await qp.fill_slots(state)

        expl.assert_not_called()
        assert (result.get("cost_diagnostics") or {}).get(
            "explanations_avoided_core_failed", 0
        ) >= 1

    @pytest.mark.asyncio
    async def test_blind_fail_no_explanation_call(self):
        slot = _slot()
        generated = _core()
        expl = AsyncMock()

        async def fake_blind(*_a, **_k):
            return _blind_disagree()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(qp, "_finalize_bank_batch_explanation", expl):
            result = await qp.fill_slots(state)

        expl.assert_not_called()
        assert result.get("approved") == []
        assert (result.get("cost_diagnostics") or {}).get(
            "explanations_avoided_core_failed", 0
        ) >= 1

    @pytest.mark.asyncio
    async def test_cognitive_mismatch_no_explanation_call(self):
        slot = _slot(target_difficulty="easy")
        generated = _core()
        expl = AsyncMock()

        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            # 3*8=24 → Difficult vs Easy target
            return _scores(3), _flags_ok()

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(qp, "_finalize_bank_batch_explanation", expl):
            result = await qp.fill_slots(state)

        expl.assert_not_called()
        assert result.get("approved") == []

    @pytest.mark.asyncio
    async def test_core_valid_triggers_exactly_one_explanation_generation(self):
        slot = _slot()
        generated = _core()
        gen_expl = AsyncMock(return_value="Barter means exchange of goods without money.")
        val_expl = AsyncMock(return_value=(True, []))

        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(
            qp, "_generate_explanation_for_core", gen_expl
        ), patch.object(qp, "_validate_explanation_only", val_expl):
            result = await qp.fill_slots(state)

        assert gen_expl.await_count == 1
        assert val_expl.await_count == 1
        assert len(result.get("approved") or []) == 1
        accepted = result["approved"][0]
        assert accepted["explanation"].startswith("Barter means")
        assert accepted.get("core_validated") is True
        cost = result.get("cost_diagnostics") or {}
        assert cost.get("explanation_generation_calls") == 1
        assert cost.get("explanation_validation_calls") == 1

    @pytest.mark.asyncio
    async def test_explanation_invalid_retries_without_changing_core(self):
        slot = _slot()
        generated = _core()
        frozen_stem = generated["question"]
        frozen_opts = list(generated["options"])
        frozen_idx = list(generated["correct_indices"])
        calls = {"n": 0}

        async def fake_expl_gen(slot_arg, core, state, excerpt, rejection_feedback=None, **kwargs):
            calls["n"] += 1
            assert core["question"] == frozen_stem
            assert core["options"] == frozen_opts
            assert core["correct_indices"] == frozen_idx
            if calls["n"] == 1:
                return "Bad explanation that will fail."
            return "Barter is exchange of goods without using money."

        async def fake_expl_val(slot_arg, core, explanation, state, excerpt, **kwargs):
            assert core["question"] == frozen_stem
            assert core["options"] == frozen_opts
            if "Bad explanation" in explanation:
                return False, ["explanation contradicts the keyed answer"]
            return True, []

        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(
            qp, "_generate_explanation_for_core", side_effect=fake_expl_gen
        ), patch.object(
            qp, "_validate_explanation_only", side_effect=fake_expl_val
        ):
            result = await qp.fill_slots(state)

        assert calls["n"] == 2  # initial + 1 corrective retry
        assert len(result["approved"]) == 1
        accepted = result["approved"][0]
        assert accepted["question"] == frozen_stem
        assert accepted["options"] == frozen_opts
        assert accepted["correct_indices"] == frozen_idx
        assert "exchange of goods" in accepted["explanation"]
        cost = result.get("cost_diagnostics") or {}
        assert cost.get("explanation_retry_calls") == 1
        assert cost.get("explanation_retries_succeeded") == 1
        assert cost.get("explanation_validation_failures") == 1

    @pytest.mark.asyncio
    async def test_explanation_retry_exhausted_never_accepted(self):
        slot = _slot()
        generated = _core()

        async def fake_expl_gen(*_a, **_k):
            return "Still bad explanation."

        async def fake_expl_val(*_a, **_k):
            return False, ["explanation is invalid"]

        state = {
            "slots": [slot.to_dict()],
            "chapter_chunks": {"1": ["Barter is exchange without money."]},
            "bank_batch_mode": True,
            "max_slot_attempts": 1,
            "slot_concurrency": 1,
            "book_grounded": True,
            "language": "en",
            "bank_duplicate_seed_texts": [],
            "bank_duplicate_seed_questions": [],
        }
        with patch.object(
            qp, "_generate_for_slot", AsyncMock(return_value=generated)
        ), patch.object(qp, "_blind_solve", AsyncMock(return_value=_blind_ok())), patch.object(
            qp, "_validate_cognitive_quality", AsyncMock(return_value=(_scores(1), _flags_ok()))
        ), patch.object(
            qp, "_generate_explanation_for_core", side_effect=fake_expl_gen
        ), patch.object(
            qp, "_validate_explanation_only", side_effect=fake_expl_val
        ):
            result = await qp.fill_slots(state)

        assert result.get("approved") == []
        assert len(result.get("failed_slots") or []) == 1
        cost = result.get("cost_diagnostics") or {}
        assert cost.get("explanation_retries_failed") == 1
        assert cost.get("explanation_generation_calls") == 2


class TestBlindUnchangedAndFinalPaper:
    def test_blind_solver_still_answer_key_blind(self):
        src = inspect.getsource(qp._blind_solve)
        assert "correct_indices" not in src or "Do NOT" in qp.BLIND_SOLVER_SYSTEM
        assert "generated.get('explanation')" not in src
        assert "target_difficulty" not in src

    def test_final_paper_graph_unchanged(self):
        paper_src = inspect.getsource(qp.build_question_paper_graph)
        assert "_finalize_bank_batch_explanation" not in paper_src
        assert "CoreGeneratedQuestion" not in paper_src

    def test_bank_generate_uses_core_schema(self):
        src = inspect.getsource(qp._generate_for_slot)
        assert "CoreGeneratedQuestion" in src
        assert "Do NOT write an explanation" in src

    def test_concurrent_blind_cognitive_still_present(self):
        src = inspect.getsource(qp._validate_slot_independently)
        assert "asyncio.gather" in src
        assert "_blind_solve" in src
        assert "_validate_cognitive_quality" in src
        assert "require_explanation_valid" in src


class TestDiagnosticsShape:
    def test_cost_diagnostics_include_explanation_fields(self):
        d = empty_bank_cost_diagnostics()
        assert "explanations_avoided_core_failed" in d
        assert "cores_rejected_before_explanation" in d
        assert "core_generation_llm_calls" in d
        assert "cores_produced" in d
        assert "core_generation_failures" in d
        assert "length_recovery_extra_calls" in d
        assert "core_validated_count" in d
        assert "explanation_generation_calls" in d
        assert "explanation_validation_calls" in d
        assert "explanation_retry_calls" in d
        d["generated_attempts"] = 5
        d["explanation_generation_calls"] = 2
        d["explanation_validation_calls"] = 2
        d["blind_solver_calls"] = 3
        d["cognitive_quality_calls"] = 3
        d["core_validated_count"] = 2
        d["explanations_avoided_core_failed"] = 3
        out = finalize_bank_cost_diagnostics(d)
        assert out["core_generation_calls"] == 5
        assert out["cores_produced"] == 5
        assert out["total_llm_calls"] == 5 + 3 + 3 + 2 + 2
