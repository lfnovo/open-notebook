"""NFO Step 2 — grounding, construction, and grade appropriateness (offline)."""

import inspect
from unittest.mock import patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import format_assigned_intent_guidance
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    evaluate_mcq_structural_rules,
    evaluate_unnecessary_source_references,
    map_cognitive_score,
    run_bank_batch_early_gates,
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


def _question(text, **overrides):
    q = {
        "question": text,
        "options": [
            "A spending and income budget plan",
            "A tax that replaces a budget",
            "Bank interest in a budget",
            "A savings budget goal",
            "Job income without a budget",
        ],
        "correct_indices": [0],
        "explanation": "A budget plans income and spending.",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "answer": "A",
    }
    q.update(overrides)
    return q


def _flags(**overrides):
    flags = {
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
        "reasons": [],
    }
    flags.update(overrides)
    return flags


def _scores():
    return {
        "knowledge": 2,
        "reasoning": 1,
        "context": 1,
        "application": 1,
        "interpretation": 1,
        "decision_making": 1,
        "concept_integration": 1,
        "distractor_quality": 2,
    }


def _validate(question, flags=None, slot=None):
    return apply_independent_validation(
        slot=slot or _slot(),
        criterion_scores=_scores(),
        quality_flags=flags if flags is not None else _flags(),
        question=question,
        existing_question_texts=[],
        book_grounded=True,
    )


class TestNfoStep2GroundingAndConstruction:
    def test_grounded_direct_chapter_concept_passes(self):
        result = _validate(_question("What is a household budget?"))
        assert result["passed"] is True

    def test_straightforward_application_passes(self):
        result = _validate(
            _question(
                "A student earns allowance and pays for lunch. Which choice shows using a budget?"
            )
        )
        assert result["passed"] is True

    def test_unrelated_external_concept_fails_via_quality_flag(self):
        result = _validate(
            _question("What is a credit-default swap?"),
            flags=_flags(no_unrelated_external_knowledge=False, grounded_in_material=False),
        )
        assert result["passed"] is False
        assert any("unrelated" in r or "grounded" in r for r in result["validation_reasons"])

    def test_unnecessary_chapter_reference_fails_deterministically(self):
        stem = "In this chapter, what is a household budget?"
        assert evaluate_unnecessary_source_references(stem)
        result = _validate(_question(stem))
        assert result["passed"] is False
        assert any(
            "source" in r or "stand on its own" in r for r in result["validation_reasons"]
        )

    def test_self_contained_natural_question_passes(self):
        result = _validate(_question("What is a household budget?"))
        assert result["passed"] is True
        assert not evaluate_unnecessary_source_references("What is a household budget?")

    def test_mechanical_textbook_wording_fails_via_quality_flag(self):
        result = _validate(
            _question("A budget is a plan for income and spending?"),
            flags=_flags(natural_assessment_wording=False),
        )
        assert result["passed"] is False
        assert any("copies the source" in r for r in result["validation_reasons"])

    def test_clear_grade_9_wording_passes(self):
        result = _validate(
            _question("What is a household budget?"),
            slot=_slot(grade="9", target_difficulty="easy"),
        )
        assert result["passed"] is True

    def test_age_inappropriate_wording_fails_via_grade_flag(self):
        result = _validate(
            _question("What is the convexity-adjusted duration of a barbell portfolio?"),
            flags=_flags(grade_appropriate=False),
            slot=_slot(grade="9", target_difficulty="easy"),
        )
        assert result["passed"] is False
        assert any("grade" in r.lower() for r in result["validation_reasons"])

    def test_realistic_concise_scenario_passes(self):
        result = _validate(
            _question(
                "Maya has $20 and wants to buy a $12 lunch. How much will she have left?"
            )
        )
        assert result["passed"] is True

    def test_irrelevant_storytelling_fails_via_quality_flag(self):
        result = _validate(
            _question(
                "After a long story about Maya's holiday, her dog, and her neighbours, "
                "what is a budget?"
            ),
            flags=_flags(scenario_focused=False),
        )
        assert result["passed"] is False
        assert any("scenario" in r for r in result["validation_reasons"])

    def test_grade_and_difficulty_remain_separate(self):
        assert "Grade and Difficulty are separate" in qp.GENERATOR_SYSTEM
        assert "independent of difficulty" in inspect.getsource(qp._generate_for_slot)
        assert "independent of grade" in inspect.getsource(qp._generate_for_slot)
        assert "Do not infer a requested difficulty" in inspect.getsource(
            qp._validate_cognitive_quality
        )
        easy_grade9 = _validate(
            _question("What is a household budget?"),
            slot=_slot(grade="9", target_difficulty="easy"),
        )
        assert easy_grade9["passed"] is True
        assert easy_grade9["validated_cognitive_difficulty"] == "easy"
        assert easy_grade9["target_difficulty"] == "easy"
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"

    def test_step1_structural_helper_unchanged_by_source_reference_check(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["Cash", "Credit", "Barter", "Loan", "Tax"],
            correct_indices=[0],
            question_text="In this chapter, what is cash?",
        )
        assert reasons == []

    def test_early_gates_treat_source_reference_as_deterministic(self):
        reasons, cat = run_bank_batch_early_gates(
            slot=_slot(),
            generated=_question("On page 12, what is a budget?"),
            existing_question_texts=[],
            existing_questions=[],
        )
        assert cat == "deterministic"
        assert reasons

    def test_intent_guidance_reuses_concept_and_objective(self):
        block = format_assigned_intent_guidance(
            {
                "intent_id": "i1",
                "topic": "Budgeting",
                "sub_topic": "Household budget",
                "concept": "A budget plans income and spending",
                "objective": "Identify what a household budget is",
                "cognitive_form": "define",
                "source_section": "Ch1",
            }
        )
        assert "concept:" in block
        assert "objective:" in block
        assert "cognitive_form:" in block
        assert "What concept is this testing?" in block
        assert "A budget plans income and spending" in block

    def test_cognitive_thresholds_and_refill_constants_unchanged(self):
        assert map_cognitive_score(8) == "easy"
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_no_new_llm_validator_class(self):
        assert "IndependentValidatorOutput" in inspect.getsource(qp)
        assert "class GroundingValidatorOutput" not in inspect.getsource(qp)

    def test_blind_solver_still_omits_answer_key_and_difficulty(self):
        src = inspect.getsource(qp._blind_solve)
        assert "generated.get('explanation')" not in src
        assert "generated.get('correct_indices')" not in src
        assert "slot.target_difficulty" not in src


class TestNfoStep2MetadataReachesGeneration:
    @pytest.mark.asyncio
    async def test_book_chapter_grade_reach_generator_prompt(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system
            captured["user"] = user_prompt

            class R:
                def model_dump(self):
                    return {
                        "question": "What is a household budget?",
                        "topic": "Budgeting",
                        "sub_topic": "Household budget",
                        "options": ["A", "B", "C", "D", "E"],
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "A budget plans income and spending.",
                    }

            return R()

        slot = _slot(grade="9", chapter=1, chapter_title="Chapter 1")
        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                slot,
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                    "language": "en",
                    "book_id": "question_book:o0chwk6eqt9rjcwmluas",
                    "topic": "Personal Finance",
                },
                "A budget is a plan for income and spending.",
                None,
            )

        assert "question_book:o0chwk6eqt9rjcwmluas" in captured["user"]
        assert "Grade:" in captured["user"]
        assert "hard constraint" in captured["user"]
        assert "9" in captured["user"]
        assert "Chapter: 1" in captured["user"]
        assert "independent of grade" in captured["user"]
        assert "CONCEPT AND LEARNING OBJECTIVE" in captured["system"]
        assert "BOOK-GROUNDED MODE" in captured["system"]
        assert "Do not take a textbook sentence" in captured["system"]

    def test_quality_validator_prompt_keeps_grade_separate_from_difficulty(self):
        src = inspect.getsource(qp._validate_cognitive_quality)
        assert "Book ID:" in src
        assert "Grade and Difficulty are separate" in src
        assert "target_difficulty" not in src
        assert "criterion_scores" in inspect.getsource(qp.IndependentValidatorOutput)
        assert "concept_relevant" in inspect.getsource(qp.IndependentValidatorOutput)
        assert "no_unrelated_external_knowledge" in inspect.getsource(
            qp.IndependentValidatorOutput
        )
        assert "distractors_ok" in qp.VALIDATOR_SYSTEM
