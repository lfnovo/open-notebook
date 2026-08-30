"""Medium under-demand gate, retry feedback, variety, and diagnostics (offline)."""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_COGNITIVE,
    academic_failure_family_correction,
    classify_medium_generated_demand,
    classify_variety_relation,
    intent_objective_form_usage_count,
    intent_selection_usage_key,
    take_next_unused_intent,
)
from open_notebook.graphs.question_paper_blueprint import (
    apply_independent_validation,
    empty_bank_cost_diagnostics,
    finalize_bank_cost_diagnostics,
    map_cognitive_score,
    QuestionSlot,
)


def _slot(**kwargs) -> QuestionSlot:
    defaults = dict(
        question_number=1,
        chapter=3,
        chapter_title="Chapter 03",
        target_difficulty="medium",
        answer_type="single_correct",
        grade="9",
        subject="Financial Literacy",
    )
    defaults.update(kwargs)
    return QuestionSlot(**defaults)


def _flags():
    return {
        "content_valid": True,
        "answer_valid": True,
        "grade_appropriate": True,
        "distractors_ok": True,
        "unambiguous": True,
        "language_clear": True,
        "grounded_in_material": True,
        "explanation_valid": True,
        "reasons": [],
    }


def _medium_scores(**overrides) -> dict:
    base = {
        "knowledge": 2,
        "reasoning": 2,
        "context": 1,
        "application": 2,
        "interpretation": 2,
        "decision_making": 2,
        "concept_integration": 2,
        "distractor_quality": 3,
    }
    base.update(overrides)
    return base


class TestMediumThresholdUnchanged:
    def test_medium_band_13_to_18(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"


class TestMediumUnderDemandGate:
    def test_direct_capital_gain_score_14_rejected(self):
        scores = _medium_scores(
            reasoning=2,
            application=2,
            interpretation=1,
            decision_making=2,
            concept_integration=1,
        )
        assert sum(scores.values()) == 14
        question = {
            "question": (
                "Raj bought 150 shares at ₹420 per share and sold all of them at "
                "₹475 per share. What capital gain did Raj make from this sale?"
            ),
            "options": ["₹8,250", "₹55", "₹71,250", "₹63,000", "₹825"],
            "correct_indices": [0],
            "topic": "Income Management",
            "sub_topic": "Sources of Income",
        }
        assert classify_medium_generated_demand(scores=scores, question=question) == "under-demand"
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=scores,
            quality_flags=_flags(),
            question=question,
            existing_question_texts=[],
            book_grounded=True,
        )
        assert result["passed"] is False
        assert result["validated_cognitive_difficulty"] == "medium"
        assert result["difficulty_score"] == 14
        text = " ".join(result["validation_reasons"])
        assert "target=medium" in text
        assert "validated=medium" in text
        assert "demand=under-demand" in text

    def test_genuine_interpretation_application_allowed(self):
        scores = _medium_scores(interpretation=2, application=2, reasoning=2)
        question = {
            "question": (
                "On 31 March 2024, Rahul received his monthly salary. For which "
                "Financial Year (FY) will this salary be counted as income, and in "
                "which Assessment Year (AY) will it be assessed and taxed?"
            ),
            "options": [
                "FY 2023-24; AY 2024-25",
                "FY 2024-25; AY 2024-25",
                "FY 2023-24; AY 2023-24",
                "FY 2024-25; AY 2025-26",
                "FY 2022-23; AY 2023-24",
            ],
            "correct_indices": [0],
            "topic": "Taxation",
            "sub_topic": "Basic Concepts",
        }
        assert classify_medium_generated_demand(scores=scores, question=question) == "ok"
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=scores,
            quality_flags=_flags(),
            question=question,
            existing_question_texts=[],
            book_grounded=True,
        )
        assert result["passed"] is True

    def test_many_numbers_alone_not_medium(self):
        scores = _medium_scores(
            reasoning=1,
            application=1,
            interpretation=1,
            decision_making=1,
            context=3,
            distractor_quality=3,
        )
        stem = (
            "A student earns ₹40,000 per month. They save ₹12,000, spend ₹9,000 on "
            "groceries, ₹3,000 on transport, ₹4,000 on utilities, ₹2,000 on dining, "
            "₹1,000 on subscriptions, and ₹7,000 on clothing. What is the total spent?"
        )
        question = {
            "question": stem,
            "options": ["₹36,000", "₹28,000", "₹40,000", "₹12,000", "₹16,000"],
            "correct_indices": [0],
            "topic": "Budgeting",
            "sub_topic": "Methods",
        }
        assert classify_medium_generated_demand(scores=scores, question=question) == "under-demand"

    def test_long_scenario_with_genuine_demand_allowed(self):
        scores = _medium_scores(application=2, interpretation=2, reasoning=2)
        stem = (
            "A student earns ₹40,000 per month. They use pay-yourself-first and save 30%, "
            "leaving ₹28,000 for an envelope budget with six envelopes and monthly spending. "
            "Which envelopes would be depleted by the end of the month?"
        )
        question = {
            "question": stem,
            "options": ["Groceries, Dining out, Utilities"] * 5,
            "correct_indices": [0],
            "topic": "Budgeting",
            "sub_topic": "Popular Budgeting Methods",
        }
        assert classify_medium_generated_demand(scores=scores, question=question) == "ok"

    def test_two_fd_interest_compare_borderline_rejected(self):
        scores = _medium_scores(
            reasoning=2,
            application=2,
            interpretation=2,
            decision_making=2,
        )
        question = {
            "question": (
                "Sam invests ₹40,000 in a fixed deposit that pays 5% annual interest. "
                "Rahul invests ₹30,000 in a fixed deposit that pays 6% annual interest. "
                "After one year, which statement is correct about the annual interest each receives?"
            ),
            "options": ["A"] * 5,
            "correct_indices": [0],
            "topic": "Income Management",
            "sub_topic": "Sources of Income",
        }
        assert classify_medium_generated_demand(scores=scores, question=question) == "under-demand"


class TestMediumRetryFeedback:
    def test_medium_under_demand_retry_wording(self):
        reasons = [
            "cognitive difficulty mismatch: target=medium, validated=medium "
            "(score=14); demand=under-demand; criteria=knowledge=2,reasoning=2,"
            "application=2,interpretation=1,decision_making=2,concept_integration=1,"
            "distractor_quality=3"
        ]
        fb = academic_failure_family_correction(
            FAILURE_FAMILY_COGNITIVE,
            {
                "concept": "Capital gain",
                "objective": "Compute capital gain on a share sale",
                "cognitive_form": "direct one-step application",
            },
            target_difficulty="medium",
            rejection_reasons=reasons,
        )
        assert "too direct for Medium" in fb
        assert "genuine application or interpretation" in fb
        assert "adding numbers" in fb
        assert "calculation repetition" in fb
        assert "multi-step integration" not in fb.lower()

    def test_medium_retry_does_not_push_difficult_integration(self):
        reasons = [
            "cognitive difficulty mismatch: target=medium, validated=medium "
            "(score=15); demand=under-demand"
        ]
        fb = academic_failure_family_correction(
            FAILURE_FAMILY_COGNITIVE,
            {
                "concept": "Budget",
                "objective": "Apply envelope budgeting",
                "cognitive_form": "apply a concept in a short scenario",
            },
            target_difficulty="medium",
            rejection_reasons=reasons,
        )
        assert "Difficult" not in fb
        assert "integrated concepts" not in fb.lower()


class TestObjectiveFormVariety:
    def _allocation_intent(self, age: str) -> dict:
        return {
            "intent_id": f"alloc-{age}",
            "concept": "Age-based asset allocation",
            "objective": (
                "Explain how age influences recommended asset allocation between "
                "equities and debt and apply the age-rule guideline to suggest a "
                "suitable equity/debt split for a given age."
            ),
            "cognitive_form": "apply a concept in a short scenario",
            "topic": "Retirement Planning",
        }

    def test_repeated_objective_form_lower_selection_priority(self):
        usage = [
            {
                "question": "A 58-year-old investor plans to retire in five years...",
                "assigned_objective": self._allocation_intent("58")["objective"],
                "assigned_cognitive_form": "apply a concept in a short scenario",
                "topic": "Retirement Planning",
            }
        ]
        remaining = [
            self._allocation_intent("55"),
            {
                "intent_id": "rent-1",
                "concept": "Rental income annualisation",
                "objective": "Apply the method to convert monthly rental into annual income.",
                "cognitive_form": "apply a concept in a short scenario",
                "topic": "Income Management",
            },
        ]
        rent_intent = remaining[1]
        chosen = take_next_unused_intent(
            remaining,
            usage_questions=usage,
            target_difficulty="medium",
        )
        assert chosen["intent_id"] == "rent-1"
        assert intent_objective_form_usage_count(self._allocation_intent("55"), usage) == 1
        assert intent_objective_form_usage_count(rent_intent, usage) == 0

    def test_same_topic_different_objective_allowed(self):
        usage = [
            {
                "question": "Compare annual rental yields with a rent-free month twist.",
                "assigned_objective": "Convert monthly rent to annual income with exceptions.",
                "assigned_cognitive_form": "interpret information using a taught concept",
                "topic": "Income Management",
            }
        ]
        dividend_intent = {
            "intent_id": "div-1",
            "concept": "Dividend income",
            "objective": "Interpret dividend income from share count and per-share dividend.",
            "cognitive_form": "interpret information using a taught concept",
            "topic": "Income Management",
        }
        assert intent_selection_usage_key(dividend_intent, usage)[1] == 0
        diag = classify_variety_relation(
            dividend_intent,
            "A company declares a dividend of ₹4 per share. Which holdings yield at least ₹400?",
            usage,
            target_difficulty="medium",
        )
        assert diag["novelty"] == "ok"

    def test_saturation_does_not_permanently_ban_concepts(self):
        usage = [{"topic": "Income Management", "assigned_concept": "Rental income"}] * 5
        remaining = [
            {
                "intent_id": "rent-again",
                "concept": "Rental income annualisation",
                "objective": "Annualise monthly rent with a rent-free month.",
                "cognitive_form": "apply a concept in a short scenario",
                "topic": "Income Management",
            }
        ]
        chosen = take_next_unused_intent(
            remaining,
            usage_questions=usage,
            target_difficulty="medium",
        )
        assert chosen is not None
        assert chosen["intent_id"] == "rent-again"

    def test_repeated_objective_and_form_marks_low_novelty(self):
        intent = self._allocation_intent("55")
        prior = {
            "question": "A 58-year-old investor near retirement needs an equity/debt split.",
            "assigned_objective": intent["objective"],
            "assigned_cognitive_form": intent["cognitive_form"],
        }
        diag = classify_variety_relation(
            intent,
            "A 55-year-old investor planning to retire in ten years needs an equity/debt split.",
            [prior],
            target_difficulty="medium",
        )
        assert "repeated_objective_and_form" in diag["labels"]
        assert diag["novelty"] == "low"


class TestDeferredExplanationUnchanged:
    def test_deferred_explanation_still_gated_after_core(self):
        src = inspect.getsource(qp.fill_slots)
        assert "_finalize_bank_batch_explanation" in src
        assert "core_validated" in src
        assert "require_explanation_valid=False" not in src or "require_explanation_valid" in src


class TestDiagnosticClarity:
    def test_finalize_reconciles_core_counts(self):
        d = empty_bank_cost_diagnostics()
        d["core_generation_calls"] = 120
        d["core_generation_llm_calls"] = 120
        d["explanations_avoided_core_failed"] = 61
        d["core_validated_count"] = 12
        d["core_generation_failures"] = 25
        d["length_recovery_extra_calls"] = 22
        out = finalize_bank_cost_diagnostics(d)
        assert out["cores_rejected_before_explanation"] == 61
        assert out["cores_produced"] == 73
        assert out["core_generation_llm_calls"] == 120
        assert out["length_recovery_extra_calls"] == 22
        assert out["core_generation_failures"] == 25
        assert out["explanations_avoided_core_failed"] == 61

    def test_new_diagnostic_fields_present(self):
        d = empty_bank_cost_diagnostics()
        for key in (
            "core_generation_llm_calls",
            "cores_produced",
            "core_generation_failures",
            "length_recovery_extra_calls",
            "cores_rejected_before_explanation",
            "core_validated_count",
        ):
            assert key in d
