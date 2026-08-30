"""NFO Step 4 — difficulty adherence (offline; no live LLM)."""

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    classify_intent_vs_difficulty,
    ensure_easy_safe_assigned_intent,
    filter_easy_safe_intents,
    intent_is_easy_safe,
)
from open_notebook.graphs.question_paper_blueprint import (
    DIFFICULTY_DEFINITIONS,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    evaluate_blind_solver,
    evaluate_mcq_structural_rules,
    evaluate_obvious_option_quality,
    evaluate_unnecessary_source_references,
    format_slot_difficulty_guidance,
    map_cognitive_score,
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


def _scores_for_total(total: int) -> dict:
    remaining = total - 8
    values = [1] * 8
    i = 0
    while remaining:
        if values[i] < 3:
            values[i] += 1
            remaining -= 1
        i = (i + 1) % 8
    keys = (
        "knowledge",
        "reasoning",
        "context",
        "application",
        "interpretation",
        "decision_making",
        "concept_integration",
        "distractor_quality",
    )
    return dict(zip(keys, values))


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


def _question():
    return {
        "question": "What is photosynthesis?",
        "options": ["A1", "A2", "A3", "A4", "A5"],
        "correct_indices": [0],
        "explanation": "A budget plans income and spending.",
        "topic": "Plants",
        "sub_topic": "Photosynthesis",
    }


class TestNfoStep4DifficultyAdherence:
    def test_easy_direct_recognition_allowed(self):
        assert intent_is_easy_safe(
            {
                "cognitive_form": "recognize an example/non-example",
                "concept": "Budget",
                "objective": "Recognize a household budget from a taught example",
            }
        )

    def test_easy_basic_comprehension_allowed(self):
        assert intent_is_easy_safe(
            {
                "cognitive_form": "direct comprehension",
                "concept": "Budget",
                "objective": "Understand that a budget plans income and spending",
            }
        )

    def test_easy_one_step_application_allowed(self):
        assert intent_is_easy_safe(
            {
                "cognitive_form": "direct one-step application",
                "concept": "Simple interest",
                "objective": "Apply the taught 10% interest rule to $100 for one year",
            }
        )

    def test_easy_multi_concept_evaluation_blocked(self):
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "identify a concept",
                "concept": "Saving and investing",
                "objective": "Evaluate two financial strategies and choose the optimal choice",
            }
        )
        assert classify_intent_vs_difficulty(
            {
                "cognitive_form": "identify a concept",
                "concept": "Saving",
                "objective": "Integrate several concepts to reach a conclusion",
            },
            "easy",
        ) == "over-demand"

    def test_easy_multi_step_causal_blocked(self):
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "direct comprehension",
                "concept": "Interest rates",
                "objective": "Explain a multi-stage causal relationship between rates and prices",
            }
        )

    def test_identify_word_alone_is_not_blocked(self):
        assert intent_is_easy_safe(
            {
                "cognitive_form": "identify a concept",
                "concept": "Budget",
                "objective": "Identify the taught definition of a household budget",
            }
        )

    def test_medium_application_allowed_by_guard(self):
        intents = [
            {
                "cognitive_form": "apply a concept in a short scenario",
                "concept": "Budget",
                "objective": "Apply a budget rule in a short spending scenario",
            }
        ]
        kept = filter_easy_safe_intents(intents, difficulty="medium")
        assert len(kept) == 1
        assert classify_intent_vs_difficulty(intents[0], "medium") == "ok"

    def test_medium_pure_recall_under_demand(self):
        assert classify_intent_vs_difficulty(
            {
                "cognitive_form": "recall a taught fact",
                "concept": "Budget",
                "objective": "Recall the definition of a budget",
            },
            "medium",
        ) == "under-demand"

    def test_difficult_analysis_allowed(self):
        assert classify_intent_vs_difficulty(
            {
                "cognitive_form": "analyze a scenario using integrated concepts",
                "concept": "Risk",
                "objective": "Analyze a scenario using integrated chapter concepts",
            },
            "difficult",
        ) == "ok"

    def test_difficult_pure_recall_under_demand(self):
        assert classify_intent_vs_difficulty(
            {
                "cognitive_form": "recall a taught fact",
                "concept": "Budget",
                "objective": "Recall the definition of a budget",
            },
            "difficult",
        ) == "under-demand"

    def test_grade_9_easy_stays_cognitively_easy(self):
        result = apply_independent_validation(
            slot=_slot(grade="9", target_difficulty="easy"),
            criterion_scores=_scores_for_total(12),
            quality_flags=_flags(),
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["passed"] is True
        assert result["validated_cognitive_difficulty"] == "easy"
        assert result["target_difficulty"] == "easy"
        assert "Grade and Difficulty are separate" in DIFFICULTY_DEFINITIONS
        easy = format_slot_difficulty_guidance("easy")
        assert "steps=0–1" in easy or "steps=0-1" in easy or "0–1" in easy

    def test_cognitive_thresholds_unchanged(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        src = inspect.getsource(map_cognitive_score)
        assert "total <= 12" in src
        assert "total <= 18" in src

    def test_mismatch_diagnostics_preserve_requested_and_validated(self):
        result = apply_independent_validation(
            slot=_slot(target_difficulty="easy"),
            criterion_scores=_scores_for_total(15),
            quality_flags=_flags(),
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
            assigned_intent={
                "intent_id": "intent-1",
                "cognitive_form": "recall a taught fact",
            },
        )
        assert result["passed"] is False
        text = " ".join(result["validation_reasons"])
        assert "target=easy" in text
        assert "validated=medium" in text
        assert "score=15" in text
        assert "demand=over-demand" in text
        assert "criteria=" in text
        assert "cognitive_form=recall a taught fact" in text
        assert result["difficulty_score"] == 15
        assert result["validated_cognitive_difficulty"] == "medium"

    def test_medium_requested_easy_score_is_under_demand(self):
        result = apply_independent_validation(
            slot=_slot(target_difficulty="medium"),
            criterion_scores=_scores_for_total(12),
            quality_flags=_flags(),
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
        )
        text = " ".join(result["validation_reasons"])
        assert "target=medium" in text
        assert "validated=easy" in text
        assert "demand=under-demand" in text

    def test_easy_safe_guard_reuses_existing_planner(self):
        remaining = [
            {
                "intent_id": "good",
                "cognitive_form": "recall a taught fact",
                "concept": "Budget",
                "objective": "Recall that a budget plans income and spending",
            }
        ]
        unsafe = {
            "intent_id": "bad",
            "cognitive_form": "identify a concept",
            "concept": "Strategy",
            "objective": "Evaluate two financial strategies",
        }
        chosen = ensure_easy_safe_assigned_intent(
            unsafe,
            remaining,
            target_difficulty="easy",
            diagnostics={},
        )
        assert chosen["intent_id"] == "good"
        fill_src = inspect.getsource(qp.fill_slots)
        assert "ensure_easy_safe_assigned_intent" in fill_src
        assert "format_slot_difficulty_guidance" in inspect.getsource(qp._generate_for_slot)
        assert "DIFFICULTY SLOT" in format_slot_difficulty_guidance("easy")
        cog_src = inspect.getsource(qp._validate_cognitive_quality)
        assert "target_difficulty" not in cog_src
        assert "Do not infer a requested difficulty" in cog_src

    def test_no_new_llm_and_steps_1_3_untouched(self):
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["Cash", "Credit", "Barter", "Loan", "Tax"],
            correct_indices=[0],
            question_text="What is cash?",
        ) == []
        assert evaluate_unnecessary_source_references("In this chapter, what is cash?")
        assert evaluate_obvious_option_quality(
            {
                "options": ["A tax on a budget"] * 5,
                "correct_indices": [0],
            }
        ) == []
        assert evaluate_blind_solver(
            {
                "independently_derived_indices": [0],
                "option_analysis": [
                    {"option": "A", "defensible": True, "reason": ""},
                    {"option": "B", "defensible": False, "reason": ""},
                    {"option": "C", "defensible": False, "reason": ""},
                    {"option": "D", "defensible": False, "reason": ""},
                    {"option": "E", "defensible": False, "reason": ""},
                ],
                "information_sufficient": True,
                "arithmetic_consistent": True,
                "no_unsupported_claims": True,
                "terminology_grounded": True,
            },
            [0],
            "single_correct",
        ) == []
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5
        assert "class DifficultyPlannerOutput" not in inspect.getsource(qp)
        easy = format_slot_difficulty_guidance("easy")
        medium = format_slot_difficulty_guidance("medium")
        hard = format_slot_difficulty_guidance("difficult")
        assert "recall" in easy.lower()
        assert "recall alone is insufficient" in medium.lower()
        assert "reasoning" in hard.lower()
