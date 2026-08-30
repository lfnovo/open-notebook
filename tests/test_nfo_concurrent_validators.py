"""Concurrent blind + cognitive validation orchestration (runtime-only).

No live LLM calls. Prompts, thresholds, and combine logic must stay unchanged.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    COGNITIVE_CRITERIA,
    MAX_SLOT_CONCURRENCY,
    QuestionSlot,
    apply_independent_validation,
    empty_bank_cost_diagnostics,
)


def _slot(**kwargs) -> QuestionSlot:
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


def _generated() -> dict:
    return {
        "question": "What is a household budget?",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "options": [
            "A spending and income budget plan",
            "A tax that replaces a budget",
            "Bank interest in a budget",
            "A savings budget goal",
            "Job income listed in a budget",
        ],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "A budget plans income and spending.",
    }


def _blind_ok() -> qp.BlindSolverOutput:
    return qp.BlindSolverOutput(
        independently_derived_indices=[0],
        option_analysis=[
            qp.OptionDefensibility(option="A", defensible=True),
            qp.OptionDefensibility(option="B", defensible=False),
            qp.OptionDefensibility(option="C", defensible=False),
            qp.OptionDefensibility(option="D", defensible=False),
            qp.OptionDefensibility(option="E", defensible=False),
        ],
        information_sufficient=True,
        arithmetic_consistent=True,
        no_unsupported_claims=True,
        terminology_grounded=True,
    )


def _blind_disagree() -> qp.BlindSolverOutput:
    out = _blind_ok()
    return out.model_copy(update={"independently_derived_indices": [1]})


def _scores(level: int = 1) -> Dict[str, int]:
    return {k: level for k in COGNITIVE_CRITERIA}


def _flags_ok() -> Dict[str, Any]:
    return {
        "content_valid": True,
        "answer_valid": True,
        "grade_appropriate": True,
        "distractors_ok": True,
        "unambiguous": True,
        "language_clear": True,
        "grounded_in_material": True,
        "explanation_valid": True,
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


def _flags_fail() -> Dict[str, Any]:
    flags = _flags_ok()
    flags["content_valid"] = False
    flags["reasons"] = ["content invalid"]
    return flags


class TestConcurrentBlindCognitiveValidation:
    @pytest.mark.asyncio
    async def test_blind_and_cognitive_overlap(self):
        events: List[Tuple[str, float]] = []

        async def fake_blind(*_a, **_k):
            events.append(("blind_start", time.perf_counter()))
            await asyncio.sleep(0.05)
            events.append(("blind_end", time.perf_counter()))
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            events.append(("cog_start", time.perf_counter()))
            await asyncio.sleep(0.05)
            events.append(("cog_end", time.perf_counter()))
            return _scores(1), _flags_ok()

        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(
            qp, "apply_independent_validation", side_effect=apply_independent_validation
        ):
            t0 = time.perf_counter()
            await qp._validate_slot_independently(
                _slot(),
                _generated(),
                {"bank_batch_mode": True, "book_grounded": True},
                "Budget plans income and spending.",
                [],
            )
            wall = time.perf_counter() - t0

        by_name = {name: ts for name, ts in events}
        assert by_name["blind_start"] < by_name["cog_end"]
        assert by_name["cog_start"] < by_name["blind_end"]
        # Overlap should finish near max(task) not sum — allow scheduling slack.
        assert wall < 0.09

    @pytest.mark.asyncio
    async def test_both_validators_called_once_and_reach_combine(self):
        blind_calls = []
        cog_calls = []
        combine_kwargs = []

        async def fake_blind(slot, generated, state, chapter_excerpt):
            blind_calls.append(
                {
                    "generated": generated,
                    "excerpt": chapter_excerpt,
                    "keys": set(generated.keys()),
                }
            )
            return _blind_ok()

        async def fake_cog(slot, generated, state, chapter_excerpt):
            cog_calls.append(
                {
                    "generated": generated,
                    "excerpt": chapter_excerpt,
                    "keys": set(generated.keys()),
                }
            )
            return _scores(1), _flags_ok()

        def capture_combine(**kwargs):
            combine_kwargs.append(kwargs)
            return apply_independent_validation(**kwargs)

        generated = _generated()
        excerpt = "Budget plans income and spending."
        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(qp, "apply_independent_validation", side_effect=capture_combine):
            result = await qp._validate_slot_independently(
                _slot(),
                generated,
                {"bank_batch_mode": True, "book_grounded": True},
                excerpt,
                [],
                cost_diagnostics=empty_bank_cost_diagnostics(),
            )

        assert len(blind_calls) == 1
        assert len(cog_calls) == 1
        assert len(combine_kwargs) == 1
        assert combine_kwargs[0]["blind_solver"] is not None
        assert combine_kwargs[0]["criterion_scores"] == _scores(1)
        assert combine_kwargs[0]["quality_flags"]["content_valid"] is True
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_blind_input_unchanged_and_blind(self):
        """Blind must not receive answer key / explanation / target difficulty / cog result."""
        seen = {}

        async def fake_blind(slot, generated, state, chapter_excerpt):
            seen["blind_args"] = (slot, generated, state, chapter_excerpt)
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        generated = _generated()
        slot = _slot(target_difficulty="easy")
        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            await qp._validate_slot_independently(
                slot,
                generated,
                {"bank_batch_mode": True, "book_grounded": True},
                "excerpt text",
                [],
            )

        _slot_arg, gen_arg, _state_arg, excerpt_arg = seen["blind_args"]
        assert gen_arg is generated
        assert excerpt_arg == "excerpt text"
        blind_src = inspect.getsource(qp._blind_solve)
        assert "correct_indices" not in blind_src
        assert "Explanation:" not in blind_src
        assert "target_difficulty" not in blind_src
        assert "Marked correct" not in blind_src
        cog_src = inspect.getsource(qp._validate_cognitive_quality)
        assert "Marked correct_indices" in cog_src
        assert "Explanation:" in cog_src
        orch_src = inspect.getsource(qp._validate_slot_independently)
        assert "asyncio.gather" in orch_src
        assert "_validate_cognitive_quality" in orch_src
        assert "_blind_solve" in orch_src

    @pytest.mark.asyncio
    async def test_cognitive_input_unchanged(self):
        seen = {}

        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(slot, generated, state, chapter_excerpt):
            seen["cog"] = (slot, generated, state, chapter_excerpt)
            return _scores(1), _flags_ok()

        generated = _generated()
        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            await qp._validate_slot_independently(
                _slot(),
                generated,
                {"bank_batch_mode": True, "book_grounded": True},
                "excerpt text",
                ["prior"],
            )

        _s, gen_arg, _st, excerpt_arg = seen["cog"]
        assert gen_arg is generated
        assert excerpt_arg == "excerpt text"
        assert "correct_indices" in gen_arg
        # Bank Batch core may carry an empty explanation placeholder.
        assert "explanation" in gen_arg

    @pytest.mark.asyncio
    async def test_blind_disagreement_still_rejects(self):
        async def fake_blind(*_a, **_k):
            return _blind_disagree()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            result = await qp._validate_slot_independently(
                _slot(),
                _generated(),
                {"bank_batch_mode": True, "book_grounded": True},
                "Budget plans income and spending.",
                [],
            )
        assert result["passed"] is False
        assert any(
            "independent solver disagrees" in r for r in result["validation_reasons"]
        )

    @pytest.mark.asyncio
    async def test_cognitive_failure_still_rejects(self):
        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_fail()

        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            result = await qp._validate_slot_independently(
                _slot(),
                _generated(),
                {"bank_batch_mode": True, "book_grounded": True},
                "Budget plans income and spending.",
                [],
            )
        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_blind_raise_does_not_accept(self):
        async def boom_blind(*_a, **_k):
            raise RuntimeError("blind boom")

        async def slow_ok_cog(*_a, **_k):
            await asyncio.sleep(0.02)
            return _scores(1), _flags_ok()

        with patch.object(qp, "_blind_solve", side_effect=boom_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=slow_ok_cog
        ), patch.object(
            qp,
            "apply_independent_validation",
            side_effect=AssertionError("must not combine"),
        ):
            with pytest.raises(RuntimeError, match="blind boom"):
                await qp._validate_slot_independently(
                    _slot(),
                    _generated(),
                    {"bank_batch_mode": True},
                    "excerpt",
                    [],
                )

    @pytest.mark.asyncio
    async def test_cognitive_raise_does_not_accept(self):
        async def ok_blind(*_a, **_k):
            await asyncio.sleep(0.02)
            return _blind_ok()

        async def boom_cog(*_a, **_k):
            raise RuntimeError("cog boom")

        with patch.object(qp, "_blind_solve", side_effect=ok_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=boom_cog
        ), patch.object(
            qp,
            "apply_independent_validation",
            side_effect=AssertionError("must not combine"),
        ):
            with pytest.raises(RuntimeError, match="cog boom"):
                await qp._validate_slot_independently(
                    _slot(),
                    _generated(),
                    {"bank_batch_mode": True},
                    "excerpt",
                    [],
                )

    @pytest.mark.asyncio
    async def test_no_new_llm_call_and_diagnostics(self):
        cost = empty_bank_cost_diagnostics()
        invoke_calls = []

        async def fake_blind(*_a, **_k):
            return _blind_ok()

        async def fake_cog(*_a, **_k):
            return _scores(1), _flags_ok()

        async def boom_invoke(*_a, **_k):
            invoke_calls.append(1)
            raise AssertionError("no live/new LLM invoke")

        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ), patch.object(qp, "_invoke_structured", side_effect=boom_invoke):
            await qp._validate_slot_independently(
                _slot(),
                _generated(),
                {"bank_batch_mode": True, "book_grounded": True},
                "excerpt",
                [],
                cost_diagnostics=cost,
            )

        assert invoke_calls == []
        assert cost["blind_solver_calls"] == 1
        assert cost["cognitive_quality_calls"] == 1
        assert cost["stage_ms_count"]["blind_solver"] == 1
        assert cost["stage_ms_count"]["cognitive_quality"] == 1
        assert cost["stage_ms_count"]["concurrent_validation"] == 1
        assert cost["stage_ms_total"]["concurrent_validation"] >= 0

    def test_slot_concurrency_unchanged(self):
        assert MAX_SLOT_CONCURRENCY == 3
        fill_src = inspect.getsource(qp.fill_slots)
        assert "slot_concurrency" in fill_src
        assert "MAX_SLOT_CONCURRENCY" in fill_src

    def test_orchestration_uses_gather_only_no_extra_llm_helpers(self):
        src = inspect.getsource(qp._validate_slot_independently)
        assert "asyncio.gather" in src
        assert src.count("_blind_solve") == 1
        assert src.count("_validate_cognitive_quality") == 1
        assert "apply_independent_validation" in src
        assert "_invoke_structured" not in src
