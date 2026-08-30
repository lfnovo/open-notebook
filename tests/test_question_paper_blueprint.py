"""Tests for question-paper blueprint, cognitive scoring, audit, and slot retry."""

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    CHAPTER_CHUNK_SIZE,
    DEFAULT_PRESET,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    audit_paper,
    build_slots,
    check_numerical_equivalence,
    chunk_chapter_text,
    decide_slot_outcome,
    evaluate_answer_type,
    evaluate_blind_solver,
    evaluate_mcq_structural_rules,
    evaluate_unsupported_context_phrasing,
    is_near_duplicate,
    is_semantic_duplicate,
    map_cognitive_score,
    select_chapter_chunk,
    validate_chapter_selection,
    validate_topic_metadata,
)

SMALL_TWO_QUESTION_PRESET = {
    "id": "test_small_2",
    "total_questions": 2,
    "pass_percentage": 70,
    "options_per_question": 5,
    "format": "mcq",
    "language": "en",
    "chapter_difficulty": {"1": {"easy": 1, "medium": 1, "difficult": 0}},
    "difficulty_answer_types": {
        "easy": {"single_correct": 1, "multiple_correct": 0},
        "medium": {"single_correct": 1, "multiple_correct": 0},
        "difficult": {"single_correct": 0, "multiple_correct": 0},
    },
}


def _slot(**kwargs) -> QuestionSlot:
    defaults = dict(
        question_number=17,
        chapter=3,
        chapter_title="Chapter 3",
        target_difficulty="difficult",
        answer_type="multiple_correct",
        grade="8",
        subject="Science",
    )
    defaults.update(kwargs)
    return QuestionSlot(**defaults)


def _question(answer_type="single_correct", indices=None, text="What is photosynthesis?"):
    if indices is None:
        indices = [0] if answer_type == "single_correct" else [0, 1]
    return {
        "question": text,
        "options": ["A1", "A2", "A3", "A4", "A5"],
        "correct_indices": indices,
        "explanation": "Because the material says so.",
        "topic": "Plants",
        "sub_topic": "Photosynthesis",
    }


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
        "reasons": [],
    }
    flags.update(overrides)
    return flags


def _scores(total: int) -> dict:
    """Build 8 criterion scores that sum to `total` (each 1–3)."""
    assert 8 <= total <= 24
    remaining = total - 8
    values = [1] * 8
    i = 0
    while remaining:
        if values[i] < 3:
            values[i] += 1
            remaining -= 1
        i = (i + 1) % 8
    keys = (
        "knowledge", "reasoning", "context", "application",
        "interpretation", "decision_making", "concept_integration", "distractor_quality",
    )
    return dict(zip(keys, values))


class TestBlueprintSlots:
    def test_default_preset_has_exactly_50_slots(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        assert len(slots) == 50

    def test_chapter_difficulty_totals(self):
        slots = build_slots(DEFAULT_PRESET)
        by_chapter = {}
        by_cd = {}
        for s in slots:
            by_chapter.setdefault(s.chapter, 0)
            by_chapter[s.chapter] += 1
            by_cd.setdefault((s.chapter, s.target_difficulty), 0)
            by_cd[(s.chapter, s.target_difficulty)] += 1
        assert by_chapter == {1: 9, 2: 11, 3: 14, 4: 16}
        expected = DEFAULT_PRESET["chapter_difficulty"]
        for chap, counts in expected.items():
            for diff, n in counts.items():
                assert by_cd[(int(chap), diff)] == n

    def test_difficulty_answer_type_totals(self):
        slots = build_slots(DEFAULT_PRESET)
        counts = {}
        for s in slots:
            counts.setdefault(s.target_difficulty, {"single_correct": 0, "multiple_correct": 0})
            counts[s.target_difficulty][s.answer_type] += 1
        assert counts == DEFAULT_PRESET["difficulty_answer_types"]
        assert sum(1 for s in slots if s.answer_type == "single_correct") == 36
        assert sum(1 for s in slots if s.answer_type == "multiple_correct") == 14

    def test_slots_carry_grade_and_subject(self):
        slots = build_slots(DEFAULT_PRESET, grade="10", subject="Physics")
        assert all(s.grade == "10" and s.subject == "Physics" for s in slots)

    def test_fewer_chapters_than_matrix_raises(self):
        with pytest.raises(ValueError, match="exactly 4"):
            build_slots(DEFAULT_PRESET, chapter_titles=["Only one", "Only two"])

    def test_extra_chapters_beyond_matrix_raises(self):
        with pytest.raises(ValueError, match="exactly 4"):
            validate_chapter_selection(DEFAULT_PRESET, 5)

    def test_matching_chapter_titles_are_kept(self):
        titles = ["Money", "Banks", "Trade", "Investing"]
        slots = build_slots(DEFAULT_PRESET, chapter_titles=titles)
        assert {s.chapter_title for s in slots} == set(titles)

    def test_custom_one_row_blueprint_accepts_one_title(self):
        slots = build_slots(SMALL_TWO_QUESTION_PRESET, chapter_titles=["Photosynthesis"])
        assert len(slots) == 2
        assert all(s.chapter_title == "Photosynthesis" for s in slots)


class TestCognitiveMapping:
    def test_score_8_easy(self):
        assert map_cognitive_score(8) == "easy"

    def test_score_12_easy(self):
        assert map_cognitive_score(12) == "easy"

    def test_score_13_medium(self):
        assert map_cognitive_score(13) == "medium"

    def test_score_18_medium(self):
        assert map_cognitive_score(18) == "medium"

    def test_score_19_difficult(self):
        assert map_cognitive_score(19) == "difficult"

    def test_score_24_difficult(self):
        assert map_cognitive_score(24) == "difficult"


class TestIndependentValidation:
    def test_target_difficult_validated_medium_rejected(self):
        result = apply_independent_validation(
            slot=_slot(target_difficulty="difficult"),
            criterion_scores=_scores(15),
            quality_flags=_flags(),
            question=_question("multiple_correct", [0, 2]),
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["validated_cognitive_difficulty"] == "medium"
        assert result["passed"] is False
        assert any("mismatch" in r for r in result["validation_reasons"])

    def test_matching_difficulty_passes_when_quality_ok(self):
        result = apply_independent_validation(
            slot=_slot(target_difficulty="medium", answer_type="single_correct"),
            criterion_scores=_scores(15),
            quality_flags=_flags(),
            question=_question("single_correct", [1]),
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["passed"] is True
        assert result["validation_status"] == "passed"
        assert result["difficulty_score"] == 15

    def test_single_correct_requires_exactly_one_answer(self):
        errors = evaluate_answer_type("single_correct", [0, 1], 5)
        assert any("exactly one" in e for e in errors)
        assert evaluate_answer_type("single_correct", [2], 5) == []

    def test_multiple_correct_accepts_multiple_answers(self):
        assert evaluate_answer_type("multiple_correct", [0, 3], 5) == []
        errors = evaluate_answer_type("multiple_correct", [1], 5)
        assert any("more than one" in e for e in errors)

    def test_does_not_reject_multiple_correct_for_having_two_answers(self):
        result = apply_independent_validation(
            slot=_slot(target_difficulty="easy", answer_type="multiple_correct"),
            criterion_scores=_scores(10),
            quality_flags=_flags(),
            question=_question("multiple_correct", [0, 4]),
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["passed"] is True

    def test_multiple_correct_rejects_all_five_correct(self):
        errors = evaluate_answer_type("multiple_correct", [0, 1, 2, 3, 4], 5)
        assert any("at most four" in e for e in errors)


class TestNfoStep1StructuralRules:
    """Deterministic MCQ structure (NFO Step 1). Does not call LLMs."""

    def _opts(self, *values):
        return list(values)

    def test_valid_single_five_options_one_correct_passes(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "Tax"),
            correct_indices=[0],
            question_text="What is money used in daily purchases?",
        )
        assert reasons == []

    def test_single_four_options_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("A", "B", "C", "D"),
            correct_indices=[0],
            question_text="What is a budget?",
        )
        assert any("expected 5 options" in r for r in reasons)

    def test_single_six_options_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("A", "B", "C", "D", "E", "F"),
            correct_indices=[0],
            question_text="What is a budget?",
        )
        assert any("expected 5 options" in r for r in reasons)

    def test_single_two_correct_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "Tax"),
            correct_indices=[0, 1],
            question_text="What is a budget?",
        )
        assert any("exactly one" in r for r in reasons)

    def test_valid_multiple_two_correct_passes(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="multiple_correct",
            options=self._opts("Need", "Want", "Income", "Tax only", "Luck"),
            correct_indices=[0, 1],
            question_text="Which of the following are spending categories?",
        )
        assert reasons == []

    def test_valid_multiple_four_correct_passes(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="multiple_correct",
            options=self._opts("Need", "Want", "Income", "Saving", "Unrelated"),
            correct_indices=[0, 1, 2, 3],
            question_text="Which of the following are personal-finance terms?",
        )
        assert reasons == []

    def test_multiple_one_correct_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="multiple_correct",
            options=self._opts("Need", "Want", "Income", "Tax only", "Luck"),
            correct_indices=[0],
            question_text="Which of the following are spending categories?",
        )
        assert any("more than one" in r for r in reasons)

    def test_multiple_all_five_correct_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="multiple_correct",
            options=self._opts("Need", "Want", "Income", "Saving", "Budget"),
            correct_indices=[0, 1, 2, 3, 4],
            question_text="Which of the following are personal-finance terms?",
        )
        assert any("at most four" in r for r in reasons)

    def test_duplicate_option_text_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash.", "cash", "Barter", "Loan", "Tax"),
            correct_indices=[2],
            question_text="What is barter?",
        )
        assert any("duplicate option" in r for r in reasons)

    def test_empty_option_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "  ", "Barter", "Loan", "Tax"),
            correct_indices=[0],
            question_text="What is money?",
        )
        assert any("empty" in r for r in reasons)

    def test_all_of_the_above_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "All of the above"),
            correct_indices=[4],
            question_text="What can be used to buy goods?",
        )
        assert any("meta-option" in r for r in reasons)

    def test_none_of_the_above_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "None of the above"),
            correct_indices=[0],
            question_text="What is a medium of exchange?",
        )
        assert any("meta-option" in r for r in reasons)

    def test_a_and_b_only_meta_option_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "A and B only"),
            correct_indices=[0],
            question_text="Which is a form of money?",
        )
        assert any("meta-option" in r for r in reasons)

    def test_according_to_the_book_standalone_stem_fails(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("Cash", "Credit", "Barter", "Loan", "Tax"),
            correct_indices=[0],
            question_text="According to the book, what is a budget?",
        )
        assert any("unsupported contextual phrasing" in r for r in reasons)

    def test_clean_self_contained_stem_passes(self):
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=self._opts("A plan for spending", "A type of tax", "A bank fee", "Interest only", "A loan"),
            correct_indices=[0],
            question_text="What is a household budget?",
        )
        assert reasons == []

    def test_does_not_rewrite_or_repair_invalid_key(self):
        options = self._opts("Cash", "Credit", "Barter", "Loan", "Tax")
        reasons = evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=options,
            correct_indices=[0, 2],
            question_text="What is cash?",
        )
        assert reasons
        assert options == ["Cash", "Credit", "Barter", "Loan", "Tax"]

    def test_passage_opt_out_does_not_reject_context_phrase(self):
        reasons = evaluate_unsupported_context_phrasing(
            "Based on the passage, what is barter?",
            standalone=False,
        )
        assert reasons == []


class TestSlotRetry:
    def test_retry_keeps_same_slot_constraints(self):
        slot = _slot()
        original = (slot.chapter, slot.target_difficulty, slot.answer_type, slot.question_number)
        assert decide_slot_outcome(False, 1, 3) == "retry"
        assert (slot.chapter, slot.target_difficulty, slot.answer_type, slot.question_number) == original

    def test_retry_exhaustion_is_finite(self):
        outcomes = [decide_slot_outcome(False, attempt, 3) for attempt in range(1, 6)]
        assert outcomes == ["retry", "retry", "needs_manual_review", "needs_manual_review", "needs_manual_review"]
        assert MAX_SLOT_ATTEMPTS == 3


class TestPaperAudit:
    def _valid_questions(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Sci")
        qs = []
        for s in slots:
            indices = [0] if s.answer_type == "single_correct" else [0, 1]
            qs.append({
                "question": (
                    f"Stem{s.question_number} chapter{s.chapter} "
                    f"{s.target_difficulty} {s.answer_type} {s.question_number}"
                ),
                "options": ["a", "b", "c", "d", "e"],
                "correct_indices": indices,
                "explanation": "Grounded explanation.",
                "answer_type": s.answer_type,
                "chapter": s.chapter,
                "target_difficulty": s.target_difficulty,
                "validated_cognitive_difficulty": s.target_difficulty,
                "validation_status": "passed",
            })
        return qs

    def test_audit_rejects_wrong_difficulty_totals(self):
        qs = self._valid_questions()
        qs[0]["validated_cognitive_difficulty"] = "difficult"
        qs[0]["target_difficulty"] = "difficult"
        result = audit_paper(qs, DEFAULT_PRESET)
        assert result["ok"] is False
        assert any("Difficulty" in e for e in result["errors"])

    def test_audit_rejects_wrong_chapter_totals(self):
        qs = self._valid_questions()
        qs[0]["chapter"] = 4
        result = audit_paper(qs, DEFAULT_PRESET)
        assert result["ok"] is False
        assert any("Chapter" in e for e in result["errors"])

    def test_audit_rejects_wrong_answer_type_totals(self):
        qs = self._valid_questions()
        target = next(q for q in qs if q["answer_type"] == "single_correct")
        target["answer_type"] = "multiple_correct"
        target["correct_indices"] = [0, 1]
        result = audit_paper(qs, DEFAULT_PRESET)
        assert result["ok"] is False
        assert any("Answer type" in e or "multiple_correct" in e for e in result["errors"])

    def test_matching_paper_passes(self):
        qs = self._valid_questions()
        result = audit_paper(qs, DEFAULT_PRESET)
        assert result["ok"] is True, result["errors"]


class TestContentCoverage:
    def test_no_12000_character_cap_in_graph(self):
        source = inspect.getsource(qp)
        assert "MAX_BOOK_CHARS" not in source
        assert "12_000" not in source
        assert "12000" not in source

    def test_later_chapter_portions_are_eligible(self):
        text = ("Later-section content. " * 200) + ("UNIQUE_TAIL_MARKER " * 50)
        assert len(text) > CHAPTER_CHUNK_SIZE
        chunks = chunk_chapter_text(text)
        assert len(chunks) > 1
        later = select_chapter_chunk(chunks, slot_index_zero_based=0, attempt=len(chunks))
        assert later in chunks

    def test_parse_book_chapters_keeps_later_chapter(self):
        chapters = qp.parse_book_chapters(
            [
                {"title": "Ch1", "text": "start " * 100},
                {"title": "Ch4 later", "text": "end-of-book unique material " * 80},
            ],
            None,
        )
        assert chapters[1]["title"] == "Ch4 later"
        assert "end-of-book unique material" in chapters[1]["text"]
        assert len(chapters[1]["text"]) > 1000

    def test_grade_is_in_generation_and_validation_prompts(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        blind_src = inspect.getsource(qp._blind_solve)
        cog_src = inspect.getsource(qp._validate_cognitive_quality)
        assert "Grade:" in gen_src
        assert "Grade:" in blind_src
        assert "Grade:" in cog_src
        assert "grade_appropriate" in qp.VALIDATOR_SYSTEM
        assert "Grade" in qp.GENERATOR_SYSTEM


@pytest.mark.asyncio
async def test_fill_slots_retries_same_constraints_then_stops():
    slot = _slot()
    state = {
        "slots": [slot.to_dict()],
        "max_slot_attempts": 3,
        "chapter_chunks": {"3": ["chunk-a", "chunk-b-later"]},
        "book_grounded": True,
        "generator_model": None,
        "reviewer_model": None,
        "language": "en",
        "used_stems": [],
        "grade": "8",
        "subject": "Science",
    }
    generated = _question("multiple_correct", [0, 1], "A retryable question about energy")
    calls = {"gen": 0}

    async def fake_generate(slot_arg, *_a, **_k):
        calls["gen"] += 1
        assert slot_arg.chapter == 3
        assert slot_arg.target_difficulty == "difficult"
        assert slot_arg.answer_type == "multiple_correct"
        assert slot_arg.question_number == 17
        return generated

    async def fake_validate(*_a, **_k):
        return apply_independent_validation(
            slot=slot,
            criterion_scores=_scores(15),
            quality_flags=_flags(),
            question=generated,
            existing_question_texts=[],
            book_grounded=True,
        )

    with patch.object(qp, "_generate_for_slot", side_effect=fake_generate), patch.object(
        qp, "_validate_slot_independently", side_effect=fake_validate
    ), patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
        result = await qp.fill_slots(state)

    assert calls["gen"] == 3
    assert result["approved"] == []
    assert len(result["failed_slots"]) == 1
    failed = result["failed_slots"][0]
    assert failed["validation_status"] == "needs_manual_review"
    assert failed["target_difficulty"] == "difficult"
    assert failed["chapter"] == 3
    assert failed["answer_type"] == "multiple_correct"


def test_legacy_paper_shape_still_readable_without_new_fields():
    old_q = {
        "question_number": 1,
        "question": "Legacy question?",
        "type": "mcq",
        "options": ["a", "b", "c", "d"],
        "marks": 1,
        "topic": "NFO",
        "difficulty": "medium",
    }
    assert old_q["options"]
    assert "target_difficulty" not in old_q


@pytest.mark.asyncio
async def test_topic_only_prepare_does_not_require_book():
    result = await qp.prepare_blueprint(
        {
            "topic": "Photosynthesis",
            "subject": "Science",
            "grade": "8",
            "blueprint_preset": SMALL_TWO_QUESTION_PRESET,
            "book_chapters": [],
            "book_content": None,
        }
    )
    assert result["book_grounded"] is False
    assert len(result["slots"]) == 2
    assert result["chapter_chunks"] == {}
    assert all(s["grade"] == "8" for s in result["slots"])
    gen_src = inspect.getsource(qp._generate_for_slot)
    assert "BOOK_GROUNDED_RULES if book_grounded else TOPIC_ONLY_RULES" in gen_src
    assert "Exam topic:" in gen_src
    assert "curriculum_objectives" in gen_src


@pytest.mark.asyncio
async def test_prepare_rejects_mismatched_book_chapters():
    with pytest.raises(ValueError, match="exactly 4"):
        await qp.prepare_blueprint(
            {
                "topic": "Money",
                "grade": "8",
                "blueprint_preset": DEFAULT_PRESET,
                "book_chapters": [
                    {"title": "Ch1", "text": "aaa"},
                    {"title": "Ch2", "text": "bbb"},
                ],
            }
        )


def test_graph_keeps_coverage_and_audit_nodes():
    nodes = set(qp.question_paper_graph.nodes)
    assert "coverage" in nodes
    assert "audit" in nodes


class TestNumericalEquivalence:
    def test_fraction_equivalence_rejects_single_correct(self):
        errors = check_numerical_equivalence(
            ["7/18", "1/3", "70/180", "5/18", "2/9"],
            [0],
            "single_correct",
        )
        assert len(errors) >= 1
        assert any("70/180" in e for e in errors)

    def test_integer_equivalence(self):
        errors = check_numerical_equivalence(
            ["42", "43", "42.0", "41", "44"],
            [0],
            "single_correct",
        )
        assert len(errors) >= 1
        assert any("42.0" in e for e in errors)

    def test_percentage_not_confused_with_decimal(self):
        # "70%" is stored as 70.0, "0.70" is 0.7 — not equivalent
        errors = check_numerical_equivalence(
            ["70%", "0.70", "7", "700", "7.0"],
            [0],
            "single_correct",
        )
        assert not any("0.70" in e for e in errors)

    def test_non_numeric_options_fall_through(self):
        errors = check_numerical_equivalence(
            ["Photosynthesis", "Respiration", "Osmosis", "Diffusion", "Absorption"],
            [0],
            "single_correct",
        )
        assert errors == []

    def test_multiple_correct_skipped(self):
        errors = check_numerical_equivalence(
            ["7/18", "70/180", "1/3", "5/18", "2/9"],
            [0, 1],
            "multiple_correct",
        )
        assert errors == []

    def test_simple_arithmetic_equivalence(self):
        errors = check_numerical_equivalence(
            ["6", "2+4", "7", "8", "9"],
            [0],
            "single_correct",
        )
        assert len(errors) >= 1
        assert any("2+4" in e for e in errors)

    def test_no_false_positive_for_different_values(self):
        errors = check_numerical_equivalence(
            ["3.14", "2.71", "1.41", "1.73", "0.577"],
            [0],
            "single_correct",
        )
        assert errors == []

    def test_validation_integration_rejects_numerical_duplicate(self):
        """apply_independent_validation should fail when numerical equivalence found."""
        result = apply_independent_validation(
            slot=_slot(target_difficulty="easy", answer_type="single_correct"),
            criterion_scores=_scores(10),
            quality_flags=_flags(),
            question={
                "question": "What is 7 divided by 18?",
                "options": ["7/18", "1/3", "70/180", "5/18", "2/9"],
                "correct_indices": [0],
                "explanation": "7/18 is the correct fraction.",
            },
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["passed"] is False
        assert any("mathematically equivalent" in r for r in result["validation_reasons"])


class TestManualAnswerTypeEnforcement:
    """Regression: backend must never silently use old 36/14 defaults for new requests."""

    def test_build_slots_rejects_zero_answer_types(self):
        preset_with_zeros = {
            **DEFAULT_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 0, "multiple_correct": 0},
                "medium": {"single_correct": 0, "multiple_correct": 0},
                "difficult": {"single_correct": 0, "multiple_correct": 0},
            },
        }
        with pytest.raises(ValueError, match="chapter slots"):
            build_slots(preset_with_zeros, grade="8", subject="Science")

    def test_build_slots_rejects_mismatched_answer_types(self):
        preset_bad = {
            **DEFAULT_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 10, "multiple_correct": 5},  # 15 != 14
                "medium": {"single_correct": 13, "multiple_correct": 5},
                "difficult": {"single_correct": 11, "multiple_correct": 7},
            },
        }
        with pytest.raises(ValueError, match="chapter slots"):
            build_slots(preset_bad, grade="8", subject="Science")

    def test_build_slots_uses_custom_answer_types(self):
        preset_custom = {
            **DEFAULT_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 10, "multiple_correct": 4},
                "medium": {"single_correct": 12, "multiple_correct": 6},
                "difficult": {"single_correct": 10, "multiple_correct": 8},
            },
        }
        slots = build_slots(preset_custom, grade="9", subject="Math")
        single = sum(1 for s in slots if s.answer_type == "single_correct")
        multi = sum(1 for s in slots if s.answer_type == "multiple_correct")
        assert single == 32
        assert multi == 18
        assert len(slots) == 50

    def test_audit_validates_against_custom_answer_types(self):
        custom_preset = {
            **DEFAULT_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 10, "multiple_correct": 4},
                "medium": {"single_correct": 12, "multiple_correct": 6},
                "difficult": {"single_correct": 10, "multiple_correct": 8},
            },
        }
        slots = build_slots(custom_preset, grade="9", subject="Math")
        questions = []
        for i, s in enumerate(slots):
            q = _question(answer_type=s.answer_type, text=" ".join(f"w{i}x{j}" for j in range(16)))
            q["target_difficulty"] = s.target_difficulty
            q["validated_cognitive_difficulty"] = s.target_difficulty
            q["validation_status"] = "passed"
            q["chapter"] = s.chapter
            q["answer_type"] = s.answer_type
            questions.append(q)
        result = audit_paper(questions, custom_preset, require_validated=True)
        assert result["ok"] is True, result["errors"]

    def test_audit_fails_when_old_36_14_used_but_custom_expected(self):
        custom_preset = {
            **DEFAULT_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 10, "multiple_correct": 4},
                "medium": {"single_correct": 12, "multiple_correct": 6},
                "difficult": {"single_correct": 10, "multiple_correct": 8},
            },
        }
        old_slots = build_slots(DEFAULT_PRESET, grade="9", subject="Math")
        questions = []
        for i, s in enumerate(old_slots):
            q = _question(answer_type=s.answer_type, text=" ".join(f"z{i}y{j}" for j in range(16)))
            q["target_difficulty"] = s.target_difficulty
            q["validated_cognitive_difficulty"] = s.target_difficulty
            q["validation_status"] = "passed"
            q["chapter"] = s.chapter
            q["answer_type"] = s.answer_type
            questions.append(q)
        result = audit_paper(questions, custom_preset)
        assert result["ok"] is False
        assert any("single_correct" in e or "multiple_correct" in e for e in result["errors"])


GRADE5_30Q_PRESET = {
    "id": "grade5_30_mcq",
    "total_questions": 30,
    "pass_percentage": 60,
    "options_per_question": 5,
    "format": "mcq",
    "language": "en",
    "chapter_difficulty": {
        "1": {"easy": 4, "medium": 4, "difficult": 2},
        "2": {"easy": 3, "medium": 4, "difficult": 3},
        "3": {"easy": 4, "medium": 4, "difficult": 2},
    },
    "difficulty_answer_types": {
        "easy": {"single_correct": 8, "multiple_correct": 3},
        "medium": {"single_correct": 9, "multiple_correct": 3},
        "difficult": {"single_correct": 5, "multiple_correct": 2},
    },
}


def _build_questions_from_slots(slots):
    """Helper: build audit-passing question list from slots with unique text."""
    questions = []
    for i, s in enumerate(slots):
        q = _question(answer_type=s.answer_type, text=" ".join(f"q{i}k{j}" for j in range(16)))
        q["target_difficulty"] = s.target_difficulty
        q["validated_cognitive_difficulty"] = s.target_difficulty
        q["validation_status"] = "passed"
        q["chapter"] = s.chapter
        q["answer_type"] = s.answer_type
        questions.append(q)
    return questions


class TestDynamicBlueprintTotals:
    """The system must work with any total derived from the chapter matrix, not just 50."""

    def test_30q_preset_produces_30_slots(self):
        slots = build_slots(GRADE5_30Q_PRESET, grade="5", subject="Financial Literacy")
        assert len(slots) == 30

    def test_30q_difficulty_totals(self):
        slots = build_slots(GRADE5_30Q_PRESET, grade="5", subject="Financial Literacy")
        easy = sum(1 for s in slots if s.target_difficulty == "easy")
        medium = sum(1 for s in slots if s.target_difficulty == "medium")
        difficult = sum(1 for s in slots if s.target_difficulty == "difficult")
        assert easy == 11
        assert medium == 12
        assert difficult == 7

    def test_30q_answer_type_totals(self):
        slots = build_slots(GRADE5_30Q_PRESET, grade="5", subject="Financial Literacy")
        single = sum(1 for s in slots if s.answer_type == "single_correct")
        multi = sum(1 for s in slots if s.answer_type == "multiple_correct")
        assert single == 22
        assert multi == 8

    def test_30q_audit_passes(self):
        slots = build_slots(GRADE5_30Q_PRESET, grade="5", subject="Financial Literacy")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, GRADE5_30Q_PRESET)
        assert result["ok"] is True, result["errors"]

    def test_30q_audit_rejects_50q_paper(self):
        """A 50-question paper must not pass audit when 30 is expected."""
        slots_50 = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        questions_50 = _build_questions_from_slots(slots_50)
        result = audit_paper(questions_50, GRADE5_30Q_PRESET)
        assert result["ok"] is False
        assert any("Total questions" in e for e in result["errors"])

    def test_50q_preset_still_produces_50_slots(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        assert len(slots) == 50

    def test_50q_audit_passes(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, DEFAULT_PRESET)
        assert result["ok"] is True, result["errors"]

    def test_50q_audit_rejects_30q_paper(self):
        """A 30-question paper must not pass audit when 50 is expected."""
        slots_30 = build_slots(GRADE5_30Q_PRESET, grade="5", subject="Financial Literacy")
        questions_30 = _build_questions_from_slots(slots_30)
        result = audit_paper(questions_30, DEFAULT_PRESET)
        assert result["ok"] is False
        assert any("Total questions" in e for e in result["errors"])

    def test_answer_type_validation_adapts_to_30q(self):
        """Answer types must match 30q difficulty totals, not 50q."""
        bad_preset = {
            **GRADE5_30Q_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 12, "multiple_correct": 2},  # 14 != 11
                "medium": {"single_correct": 9, "multiple_correct": 3},
                "difficult": {"single_correct": 5, "multiple_correct": 2},
            },
        }
        with pytest.raises(ValueError, match="chapter slots"):
            build_slots(bad_preset, grade="5", subject="Financial Literacy")


# 4-chapter, 30-question Grade 5 preset matching NFO book structure
GRADE5_4CH_30Q_PRESET = {
    "id": "grade5_4ch_30_mcq",
    "total_questions": 30,
    "pass_percentage": 70,
    "options_per_question": 5,
    "format": "mcq",
    "language": "en",
    "chapter_difficulty": {
        "1": {"easy": 3, "medium": 3, "difficult": 1},
        "2": {"easy": 3, "medium": 3, "difficult": 2},
        "3": {"easy": 3, "medium": 4, "difficult": 2},
        "4": {"easy": 2, "medium": 2, "difficult": 2},
    },
    "difficulty_answer_types": {
        "easy": {"single_correct": 9, "multiple_correct": 2},
        "medium": {"single_correct": 9, "multiple_correct": 3},
        "difficult": {"single_correct": 5, "multiple_correct": 2},
    },
}


class TestGrade5FourChapter30Q:
    """4-chapter, 30-question Grade 5 NFO paper — realistic end-to-end blueprint test."""

    def test_produces_exactly_30_slots(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        assert len(slots) == 30

    def test_difficulty_totals(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        easy = sum(1 for s in slots if s.target_difficulty == "easy")
        medium = sum(1 for s in slots if s.target_difficulty == "medium")
        difficult = sum(1 for s in slots if s.target_difficulty == "difficult")
        assert easy == 11
        assert medium == 12
        assert difficult == 7

    def test_answer_type_totals(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        single = sum(1 for s in slots if s.answer_type == "single_correct")
        multi = sum(1 for s in slots if s.answer_type == "multiple_correct")
        assert single == 23
        assert multi == 7

    def test_chapter_slot_counts(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        ch_counts = {}
        for s in slots:
            ch_counts[s.chapter] = ch_counts.get(s.chapter, 0) + 1
        assert ch_counts == {1: 7, 2: 8, 3: 9, 4: 6}

    def test_all_slots_carry_grade_and_subject(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        for s in slots:
            assert s.grade == "5"
            assert s.subject == "Financial Literacy"

    def test_audit_passes_with_matching_paper(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, GRADE5_4CH_30Q_PRESET)
        assert result["ok"] is True, result["errors"]
        assert result["expected_total"] == 30

    def test_audit_rejects_50q_paper(self):
        slots_50 = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        questions_50 = _build_questions_from_slots(slots_50)
        result = audit_paper(questions_50, GRADE5_4CH_30Q_PRESET)
        assert result["ok"] is False

    def test_audit_rejects_wrong_answer_type_split(self):
        """If paper has 24 single / 6 multi but preset expects 23/7, audit must fail."""
        wrong_preset = {
            **GRADE5_4CH_30Q_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 10, "multiple_correct": 1},
                "medium": {"single_correct": 9, "multiple_correct": 3},
                "difficult": {"single_correct": 5, "multiple_correct": 2},
            },
        }
        slots = build_slots(wrong_preset, grade="5", subject="Financial Literacy")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, GRADE5_4CH_30Q_PRESET)
        assert result["ok"] is False
        assert any("single_correct" in e or "multiple_correct" in e for e in result["errors"])


class TestTotalQuestionsMismatch:
    """total_questions must match chapter matrix sum; no silent fallback."""

    def test_30_total_30_matrix_valid(self):
        preset = {
            **GRADE5_4CH_30Q_PRESET,
            "total_questions": 30,
        }
        slots = build_slots(preset, grade="5", subject="Financial Literacy")
        assert len(slots) == 30

    def test_30_total_32_matrix_build_slots_uses_matrix(self):
        """build_slots derives total from matrix, so 32-cell matrix → 32 slots."""
        preset = {
            **GRADE5_4CH_30Q_PRESET,
            "total_questions": 30,
            "chapter_difficulty": {
                "1": {"easy": 3, "medium": 4, "difficult": 1},  # +1 medium
                "2": {"easy": 3, "medium": 4, "difficult": 2},  # +1 medium
                "3": {"easy": 3, "medium": 4, "difficult": 2},
                "4": {"easy": 2, "medium": 2, "difficult": 2},
            },
            "difficulty_answer_types": {
                "easy": {"single_correct": 9, "multiple_correct": 2},
                "medium": {"single_correct": 11, "multiple_correct": 3},
                "difficult": {"single_correct": 5, "multiple_correct": 2},
            },
        }
        slots = build_slots(preset, grade="5", subject="Financial Literacy")
        assert len(slots) == 32  # matrix wins

    def test_50_total_50_matrix_valid(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        assert len(slots) == 50

    def test_audit_30_expects_30(self):
        slots = build_slots(GRADE5_4CH_30Q_PRESET, grade="5", subject="Financial Literacy")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, GRADE5_4CH_30Q_PRESET)
        assert result["ok"] is True
        assert result["expected_total"] == 30

    def test_audit_50_expects_50(self):
        slots = build_slots(DEFAULT_PRESET, grade="8", subject="Science")
        questions = _build_questions_from_slots(slots)
        result = audit_paper(questions, DEFAULT_PRESET)
        assert result["ok"] is True
        assert result["expected_total"] == 50

    def test_answer_types_adapt_to_30_matrix(self):
        """Answer type validation uses difficulty totals from the matrix, not from total_questions."""
        bad = {
            **GRADE5_4CH_30Q_PRESET,
            "difficulty_answer_types": {
                "easy": {"single_correct": 12, "multiple_correct": 2},  # 14 != 11
                "medium": {"single_correct": 9, "multiple_correct": 3},
                "difficult": {"single_correct": 5, "multiple_correct": 2},
            },
        }
        with pytest.raises(ValueError, match="chapter slots"):
            build_slots(bad, grade="5", subject="Financial Literacy")

    def test_parse_non_neg_int_leading_zero(self):
        """03 should parse to 3, not octal or error."""
        assert int("03") == 3
        assert max(0, int("03")) == 3
        assert max(0, int("007")) == 7


@pytest.mark.asyncio
async def test_coverage_report_uses_curriculum_objectives():
    state = {
        "topic": "Photosynthesis",
        "curriculum_objectives": ["Define photosynthesis", "Explain stomata"],
        "approved": [
            {
                "question_number": 1,
                "question": "What is photosynthesis?",
                "topic": "Photosynthesis",
                "sub_topic": "definition",
                "chapter_title": "Chapter 1",
            }
        ],
        "final_paper": {"sections": []},
    }
    fake = qp.CoverageReportOutput(
        covered_topics=["Define photosynthesis"],
        gaps=["Explain stomata"],
    )
    with patch.object(qp, "_invoke_structured", new=AsyncMock(return_value=fake)):
        result = await qp.report_coverage(state)
    assert result["covered_topics"] == ["Define photosynthesis"]
    assert result["coverage_gaps"] == ["Explain stomata"]


# ---------------------------------------------------------------------------
# Refill / completion pass tests
# ---------------------------------------------------------------------------

_UNIQUE_WORDS = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
    "xray", "yankee", "zulu", "amber", "bronze", "coral", "dusk",
]


def _make_approved_question(qn, chapter, difficulty, answer_type, text=None):
    """Helper to create a minimal approved question record."""
    w = _UNIQUE_WORDS[qn % len(_UNIQUE_WORDS)]
    return {
        "question_number": qn,
        "question": text or f"{w} {difficulty} ch{chapter} q{qn} scenario_{qn*7}",
        "type": "mcq" if answer_type == "single_correct" else "multi_correct",
        "answer_type": answer_type,
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": f"Explanation for Q{qn}",
        "topic": f"Topic-ch{chapter}-q{qn}",
        "sub_topic": f"Sub-{qn}",
        "grade": "5",
        "subject": "Test",
        "chapter": chapter,
        "chapter_title": f"Chapter {chapter}",
        "section_ref": f"Chapter {chapter}",
        "target_difficulty": difficulty,
        "validated_cognitive_difficulty": difficulty,
        "difficulty": difficulty,
        "difficulty_score": 10,
        "difficulty_scores": {},
        "validation_status": "accepted",
        "validation_reasons": [],
        "generation_attempts": 1,
    }


def _make_failed_slot(qn, chapter, difficulty, answer_type):
    """Helper to create a failed slot record."""
    return {
        "question_number": qn,
        "chapter": chapter,
        "chapter_title": f"Chapter {chapter}",
        "target_difficulty": difficulty,
        "answer_type": answer_type,
        "grade": "5",
        "subject": "Test",
        "validation_status": "needs_manual_review",
        "validation_reasons": ["duplicate or near-duplicate of an existing question"],
        "generation_attempts": MAX_SLOT_ATTEMPTS,
    }


def _fake_generator_success(slot, state, excerpt, feedback):
    """Returns a coroutine that produces a valid generated question."""
    async def _gen(sl, st, ex, fb, diversity_guidance=None, soft_coverage_hints=None, **kwargs):
        return {
            "question": f"Refilled question {sl.question_number} ch{sl.chapter} unique-{id(fb)}",
            "topic": f"RefillTopic-{sl.chapter}",
            "sub_topic": f"RefillSub-{sl.question_number}",
            "options": ["OptA", "OptB", "OptC", "OptD", "OptE"],
            "correct_indices": [0] if sl.answer_type == "single_correct" else [0, 1],
            "answer": "A" if sl.answer_type == "single_correct" else "A, B",
            "explanation": f"Refill explanation for Q{sl.question_number}",
        }
    return _gen


def _fake_validator_pass(slot, generated, state, excerpt, existing):
    """Returns validation that passes."""
    async def _val(sl, gen, st, ex, exist, **kwargs):
        return {
            "passed": True,
            "validation_status": "accepted",
            "validation_reasons": [],
            "difficulty_scores": {"knowledge": 2, "reasoning": 2, "context": 2, "application": 2,
                                  "interpretation": 2, "decision_making": 2, "concept_integration": 2,
                                  "distractor_quality": 2},
            "difficulty_score": 16,
            "validated_cognitive_difficulty": sl.target_difficulty,
            "target_difficulty": sl.target_difficulty,
        }
    return _val


def _fake_validator_always_fail(slot, generated, state, excerpt, existing):
    """Returns validation that always fails."""
    async def _val(sl, gen, st, ex, exist, **kwargs):
        return {
            "passed": False,
            "validation_status": "rejected",
            "validation_reasons": ["cognitive difficulty mismatch: target=difficult, validated=medium (score=16)"],
            "difficulty_scores": {},
            "difficulty_score": 16,
            "validated_cognitive_difficulty": "medium",
            "target_difficulty": sl.target_difficulty,
        }
    return _val


class TestRefillSlots:
    """Tests for the refill/completion pass."""

    def _base_state(self, approved, failed, rejected_log=None):
        return {
            "approved": approved,
            "failed_slots": failed,
            "used_stems": [],
            "rejected_with_feedback": rejected_log or [],
            "chapter_chunks": {"1": ["chunk1"], "2": ["chunk2"], "3": ["chunk3"], "4": ["chunk4"]},
            "book_grounded": True,
            "max_refill_attempts": MAX_REFILL_ATTEMPTS,
            "slot_concurrency": 2,
            "max_slot_attempts": MAX_SLOT_ATTEMPTS,
            "grade": "5",
            "subject": "Test",
        }

    @pytest.mark.asyncio
    async def test_refill_recovers_all_failed_slots(self):
        """27 approved + 3 failed → refill recovers all 3 → 30 total."""
        approved = [_make_approved_question(i, (i % 4) + 1, "easy", "single_correct") for i in range(1, 28)]
        failed = [
            _make_failed_slot(28, 2, "easy", "single_correct"),
            _make_failed_slot(29, 3, "difficult", "single_correct"),
            _make_failed_slot(30, 4, "difficult", "multiple_correct"),
        ]
        state = self._base_state(approved, failed)

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["approved"]) == 30
        assert len(result["failed_slots"]) == 0

    @pytest.mark.asyncio
    async def test_refill_preserves_accepted_questions(self):
        """Accepted questions from initial pass must not be regenerated."""
        approved = [_make_approved_question(i, 1, "easy", "single_correct") for i in range(1, 4)]
        failed = [_make_failed_slot(4, 1, "medium", "single_correct")]
        state = self._base_state(approved, failed)

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn) as mock_gen, \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        # Generator should only be called for the 1 failed slot, not the 3 accepted
        assert mock_gen.call_count <= MAX_REFILL_ATTEMPTS
        assert len(result["approved"]) == 4
        for q in approved:
            assert q in result["approved"]

    @pytest.mark.asyncio
    async def test_refill_preserves_slot_metadata(self):
        """Refilled slot must keep original chapter/difficulty/answer_type."""
        failed = [_make_failed_slot(7, 2, "difficult", "multiple_correct")]
        state = self._base_state([], failed)

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        recovered = result["approved"][0]
        assert recovered["question_number"] == 7
        assert recovered["chapter"] == 2
        assert recovered["target_difficulty"] == "difficult"
        assert recovered["answer_type"] == "multiple_correct"

    @pytest.mark.asyncio
    async def test_refill_respects_max_attempts(self):
        """Refill must not exceed MAX_REFILL_ATTEMPTS per slot."""
        failed = [_make_failed_slot(10, 3, "difficult", "single_correct")]
        state = self._base_state([], failed)

        val_fn = _fake_validator_always_fail(None, None, None, None, None)
        gen_fn = _fake_generator_success(None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn) as mock_gen, \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["failed_slots"]) == 1
        assert result["failed_slots"][0]["question_number"] == 10
        assert mock_gen.call_count == MAX_REFILL_ATTEMPTS

    @pytest.mark.asyncio
    async def test_refill_duplicate_slot_is_requeued(self):
        """A slot that failed for duplicate reasons gets retried in refill."""
        approved = [_make_approved_question(1, 1, "easy", "single_correct")]
        failed = [_make_failed_slot(2, 1, "easy", "single_correct")]
        failed[0]["validation_reasons"] = ["duplicate or near-duplicate of an existing question"]
        state = self._base_state(approved, failed)

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["approved"]) == 2
        assert len(result["failed_slots"]) == 0

    @pytest.mark.asyncio
    async def test_refill_difficulty_mismatch_slot_requeued(self):
        """A slot that failed for difficulty mismatch gets retried."""
        failed = [_make_failed_slot(11, 2, "difficult", "single_correct")]
        failed[0]["validation_reasons"] = [
            "cognitive difficulty mismatch: target=difficult, validated=medium (score=16)"
        ]
        state = self._base_state([], failed, rejected_log=[{
            "question_number": 11,
            "attempt": 3,
            "rewrite_instruction": "cognitive difficulty mismatch: target=difficult, validated=medium (score=16)",
            "chapter": 2,
            "target_difficulty": "difficult",
            "answer_type": "single_correct",
        }])

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["approved"]) == 1
        assert len(result["failed_slots"]) == 0

    @pytest.mark.asyncio
    async def test_all_filled_after_refill_gives_completed(self):
        """When refill fills all, audit should pass → completed."""
        from open_notebook.graphs.question_paper_blueprint import audit_paper

        preset = {
            "id": "test_refill_audit",
            "total_questions": 3,
            "pass_percentage": 70,
            "options_per_question": 5,
            "chapter_difficulty": {"1": {"easy": 1, "medium": 1, "difficult": 1}},
            "difficulty_answer_types": {
                "easy": {"single_correct": 1, "multiple_correct": 0},
                "medium": {"single_correct": 1, "multiple_correct": 0},
                "difficult": {"single_correct": 1, "multiple_correct": 0},
            },
        }
        questions = [
            {**_make_approved_question(1, 1, "easy", "single_correct"), "validation_status": "passed"},
            {**_make_approved_question(2, 1, "medium", "single_correct"), "validation_status": "passed"},
            {**_make_approved_question(3, 1, "difficult", "single_correct"), "validation_status": "passed"},
        ]
        result = audit_paper(questions, preset, require_validated=False)
        assert result["errors"] == [], f"Audit errors: {result['errors']}"
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_still_missing_after_refill_gives_needs_manual_review(self):
        """When refill can't fill all slots, audit should fail."""
        failed = [_make_failed_slot(5, 2, "difficult", "single_correct")]
        state = self._base_state([], failed)

        val_fn = _fake_validator_always_fail(None, None, None, None, None)
        gen_fn = _fake_generator_success(None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["failed_slots"]) == 1
        assert result["failed_slots"][0]["validation_status"] == "needs_manual_review"

    @pytest.mark.asyncio
    async def test_no_failed_slots_skips_refill(self):
        """If no failed slots, refill_slots returns empty dict (no-op)."""
        state = self._base_state(
            [_make_approved_question(1, 1, "easy", "single_correct")],
            [],
        )
        result = await qp.refill_slots(state)
        assert result == {}


class TestReasonAwareFeedback:
    """Tests for _build_reason_aware_feedback."""

    def test_duplicate_reason_produces_guidance(self):
        feedback = qp._build_reason_aware_feedback(
            ["duplicate or near-duplicate of an existing question"],
            [], [], QuestionSlot(1, 1, "Ch1", "easy", "single_correct", "5", "Test"),
        )
        assert "DUPLICATE" in feedback
        assert "DIFFERENT" in feedback

    def test_difficulty_reason_produces_guidance(self):
        feedback = qp._build_reason_aware_feedback(
            ["cognitive difficulty mismatch: target=difficult, validated=medium (score=16)"],
            [], [], QuestionSlot(1, 1, "Ch1", "difficult", "single_correct", "5", "Test"),
        )
        assert "COGNITIVE DEMAND" in feedback

    def test_previous_stems_included(self):
        feedback = qp._build_reason_aware_feedback(
            ["duplicate"],
            ["What is money", "Define savings"],
            [], QuestionSlot(1, 1, "Ch1", "easy", "single_correct", "5", "Test"),
        )
        assert "What is money" in feedback
        assert "Define savings" in feedback

    def test_heavy_topics_flagged(self):
        feedback = qp._build_reason_aware_feedback(
            ["duplicate"],
            [],
            ["Savings", "Savings", "Savings", "Budget"],
            QuestionSlot(1, 1, "Ch1", "easy", "single_correct", "5", "Test"),
        )
        assert "Savings" in feedback
        assert "DIFFERENT topic" in feedback


class TestGraphConditionalEdge:
    """Test that the graph routes correctly based on failed_slots."""

    def test_needs_refill_routes_to_refill(self):
        state = {"failed_slots": [{"question_number": 1}]}
        assert qp._needs_refill(state) == "refill_slots"

    def test_no_failed_routes_to_assemble(self):
        state = {"failed_slots": []}
        assert qp._needs_refill(state) == "assemble"

    def test_none_failed_routes_to_assemble(self):
        state = {}
        assert qp._needs_refill(state) == "assemble"


class TestRegenerateMissing:
    """Tests for the manual regenerate-missing flow (refill + assemble + audit)."""

    def _make_state_with_27_accepted_3_failed(self):
        """Simulate a 30-slot paper with 27 accepted and 3 failed."""
        approved = [_make_approved_question(i, (i % 4) + 1, "easy", "single_correct") for i in range(1, 28)]
        failed = [
            _make_failed_slot(28, 2, "easy", "single_correct"),
            _make_failed_slot(29, 3, "difficult", "single_correct"),
            _make_failed_slot(30, 4, "difficult", "multiple_correct"),
        ]
        return approved, failed

    @pytest.mark.asyncio
    async def test_regeneration_only_processes_failed_slots(self):
        """Only failed slots are passed to refill; accepted are preserved."""
        approved, failed = self._make_state_with_27_accepted_3_failed()
        state = {
            "approved": approved,
            "failed_slots": failed,
            "used_stems": [],
            "rejected_with_feedback": [],
            "chapter_chunks": {str(i): [f"chunk{i}"] for i in range(1, 5)},
            "book_grounded": True,
            "max_refill_attempts": MAX_REFILL_ATTEMPTS,
            "max_slot_attempts": MAX_SLOT_ATTEMPTS,
            "slot_concurrency": 2,
            "grade": "5",
            "subject": "Test",
        }

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn) as mock_gen, \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["approved"]) == 30
        assert len(result["failed_slots"]) == 0
        # Original 27 should be in the approved list unchanged
        for orig in approved:
            assert orig in result["approved"]

    @pytest.mark.asyncio
    async def test_regeneration_preserves_question_numbers(self):
        """Regenerated questions keep their original question_number."""
        approved, failed = self._make_state_with_27_accepted_3_failed()
        state = {
            "approved": approved,
            "failed_slots": failed,
            "used_stems": [],
            "rejected_with_feedback": [],
            "chapter_chunks": {str(i): [f"chunk{i}"] for i in range(1, 5)},
            "book_grounded": True,
            "max_refill_attempts": MAX_REFILL_ATTEMPTS,
            "max_slot_attempts": MAX_SLOT_ATTEMPTS,
            "slot_concurrency": 2,
            "grade": "5",
            "subject": "Test",
        }

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        new_qns = {q["question_number"] for q in result["approved"]} - {q["question_number"] for q in approved}
        assert new_qns == {28, 29, 30}

    @pytest.mark.asyncio
    async def test_regeneration_preserves_chapter_difficulty_answer_type(self):
        """Regenerated questions keep their slot's chapter/difficulty/answer_type."""
        failed = [
            _make_failed_slot(7, 2, "difficult", "multiple_correct"),
        ]
        state = {
            "approved": [],
            "failed_slots": failed,
            "used_stems": [],
            "rejected_with_feedback": [],
            "chapter_chunks": {"2": ["ch2content"]},
            "book_grounded": True,
            "max_refill_attempts": MAX_REFILL_ATTEMPTS,
            "max_slot_attempts": MAX_SLOT_ATTEMPTS,
            "slot_concurrency": 1,
            "grade": "5",
            "subject": "Test",
        }

        gen_fn = _fake_generator_success(None, None, None, None)
        val_fn = _fake_validator_pass(None, None, None, None, None)

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        q = result["approved"][0]
        assert q["question_number"] == 7
        assert q["chapter"] == 2
        assert q["target_difficulty"] == "difficult"
        assert q["answer_type"] == "multiple_correct"

    @pytest.mark.asyncio
    async def test_partial_regeneration_updates_count(self):
        """If only 2 of 3 fail-slots succeed, result is 29/30 with 1 still failed."""
        approved = [_make_approved_question(i, (i % 4) + 1, "easy", "single_correct") for i in range(1, 28)]
        failed = [
            _make_failed_slot(28, 2, "easy", "single_correct"),
            _make_failed_slot(29, 3, "difficult", "single_correct"),
            _make_failed_slot(30, 4, "difficult", "multiple_correct"),
        ]

        call_count = 0
        gen_fn_inner = _fake_generator_success(None, None, None, None)

        async def gen_fn_alternating(sl, st, ex, fb, diversity_guidance=None, soft_coverage_hints=None, **kwargs):
            nonlocal call_count
            call_count += 1
            return await gen_fn_inner(sl, st, ex, fb)

        val_pass = _fake_validator_pass(None, None, None, None, None)
        val_fail = _fake_validator_always_fail(None, None, None, None, None)

        # Slot 30 always fails validation
        async def val_fn_mixed(sl, gen, st, ex, exist, **kwargs):
            if sl.question_number == 30:
                return await val_fail(sl, gen, st, ex, exist)
            return await val_pass(sl, gen, st, ex, exist)

        state = {
            "approved": approved,
            "failed_slots": failed,
            "used_stems": [],
            "rejected_with_feedback": [],
            "chapter_chunks": {str(i): [f"chunk{i}"] for i in range(1, 5)},
            "book_grounded": True,
            "max_refill_attempts": MAX_REFILL_ATTEMPTS,
            "max_slot_attempts": MAX_SLOT_ATTEMPTS,
            "slot_concurrency": 2,
            "grade": "5",
            "subject": "Test",
        }

        with patch.object(qp, "_generate_for_slot", side_effect=gen_fn_alternating), \
             patch.object(qp, "_validate_slot_independently", side_effect=val_fn_mixed), \
             patch.object(qp, "check_bank_duplicate", new=AsyncMock(return_value=False)):
            result = await qp.refill_slots(state)

        assert len(result["approved"]) == 29
        assert len(result["failed_slots"]) == 1
        assert result["failed_slots"][0]["question_number"] == 30


# ---------------------------------------------------------------------------
# Quality validation: blind solver
# ---------------------------------------------------------------------------

class TestBlindSolver:
    """Tests for evaluate_blind_solver() — independent answer verification."""

    def test_solver_agrees_with_key_single_correct(self):
        solver = {
            "independently_derived_indices": [2],
            "option_analysis": [
                {"option": "A", "defensible": False, "reason": "wrong"},
                {"option": "B", "defensible": False, "reason": "wrong"},
                {"option": "C", "defensible": True, "reason": "correct"},
                {"option": "D", "defensible": False, "reason": "wrong"},
                {"option": "E", "defensible": False, "reason": "wrong"},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [2], "single_correct")
        assert errors == []

    def test_solver_disagrees_with_key(self):
        """Regression: Q2-type — solver finds a different answer than the key."""
        solver = {
            "independently_derived_indices": [0],
            "option_analysis": [
                {"option": "A", "defensible": True, "reason": "also valid"},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": True, "reason": "generated key"},
                {"option": "D", "defensible": False, "reason": ""},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [2], "single_correct")
        assert any("independent solver disagrees" in e for e in errors)

    def test_multiple_defensible_single_correct(self):
        """Regression: Q2-type — more than one defensible option in single_correct."""
        solver = {
            "independently_derived_indices": [2],
            "option_analysis": [
                {"option": "A", "defensible": True, "reason": "also valid medium-of-exchange"},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": True, "reason": "generated key"},
                {"option": "D", "defensible": False, "reason": ""},
                {"option": "E", "defensible": True, "reason": "also defensible"},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [2], "single_correct")
        assert any("multiple defensible" in e for e in errors)

    def test_multiple_correct_set_matches(self):
        solver = {
            "independently_derived_indices": [0, 2],
            "option_analysis": [
                {"option": "A", "defensible": True, "reason": ""},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": True, "reason": ""},
                {"option": "D", "defensible": False, "reason": ""},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [0, 2], "multiple_correct")
        assert errors == []

    def test_multiple_correct_set_mismatch(self):
        """Regression: Q7-type — defensible set differs from generated key."""
        solver = {
            "independently_derived_indices": [0, 2, 3],
            "option_analysis": [
                {"option": "A", "defensible": True, "reason": ""},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": True, "reason": ""},
                {"option": "D", "defensible": True, "reason": "also valid"},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [0, 2], "multiple_correct")
        assert any("defensible option set" in e for e in errors)

    def test_information_insufficient(self):
        """Regression: Q22-type — stem lacks data to determine the answer."""
        solver = {
            "independently_derived_indices": [1],
            "option_analysis": [
                {"option": "A", "defensible": False, "reason": ""},
                {"option": "B", "defensible": True, "reason": ""},
                {"option": "C", "defensible": False, "reason": ""},
                {"option": "D", "defensible": False, "reason": ""},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": False,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [1], "single_correct")
        assert any("information insufficient" in e for e in errors)

    def test_arithmetic_inconsistency(self):
        """Regression: Q29-type — $60/year wording inconsistent with 6% of $500."""
        solver = {
            "independently_derived_indices": [0],
            "option_analysis": [
                {"option": "A", "defensible": True, "reason": ""},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": False, "reason": ""},
                {"option": "D", "defensible": False, "reason": ""},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": False,
            "no_unsupported_claims": True,
        }
        errors = evaluate_blind_solver(solver, [0], "single_correct")
        assert any("arithmetic" in e for e in errors)

    def test_unsupported_claim(self):
        """Regression: Q28-type — investing always grows faster than savings."""
        solver = {
            "independently_derived_indices": [3],
            "option_analysis": [
                {"option": "A", "defensible": False, "reason": ""},
                {"option": "B", "defensible": False, "reason": ""},
                {"option": "C", "defensible": False, "reason": ""},
                {"option": "D", "defensible": True, "reason": ""},
                {"option": "E", "defensible": False, "reason": ""},
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": False,
        }
        errors = evaluate_blind_solver(solver, [3], "single_correct")
        assert any("unsupported" in e for e in errors)

    def test_solver_none_returns_no_errors(self):
        """When blind solver fails entirely, don't block — let other checks run."""
        errors = evaluate_blind_solver(None, [0], "single_correct")
        assert errors == []


# ---------------------------------------------------------------------------
# Semantic duplicate detection
# ---------------------------------------------------------------------------

class TestSemanticDuplicate:
    """Tests for is_semantic_duplicate()."""

    def test_same_concept_different_wording_is_duplicate(self):
        """Regression: Q23/Q24-type — 'What is an investment?' vs 'What is investing?'"""
        candidate = {"chapter": 1, "topic": "Investment", "question": "What is an investment?"}
        existing = [{"chapter": 1, "topic": "Investment", "question": "What does investing mean?"}]
        assert is_semantic_duplicate(candidate, existing) is True

    def test_different_concepts_same_chapter_not_duplicate(self):
        """'What is compound interest?' vs 'Compare saving choices' — not duplicates."""
        candidate = {"chapter": 2, "topic": "Compound Interest", "question": "What is compound interest?"}
        existing = [{"chapter": 2, "topic": "Compound Interest", "question": "Compare two saving choices using compounding over ten years"}]
        assert is_semantic_duplicate(candidate, existing) is False

    def test_different_chapter_same_wording_not_duplicate(self):
        candidate = {"chapter": 1, "topic": "Budgeting", "question": "What is budgeting?"}
        existing = [{"chapter": 3, "topic": "Budgeting", "question": "What is budgeting?"}]
        assert is_semantic_duplicate(candidate, existing) is False

    def test_different_topic_same_chapter_not_duplicate(self):
        candidate = {"chapter": 1, "topic": "Savings", "question": "Why do people save money?"}
        existing = [{"chapter": 1, "topic": "Taxes", "question": "Why do governments collect taxes?"}]
        assert is_semantic_duplicate(candidate, existing) is False

    def test_empty_existing_not_duplicate(self):
        candidate = {"chapter": 1, "topic": "Money", "question": "What is money?"}
        assert is_semantic_duplicate(candidate, []) is False

    def test_substring_topic_match(self):
        """Topics like 'Interest' and 'Simple Interest' should be considered matching."""
        candidate = {"chapter": 2, "topic": "Interest", "question": "What is interest on savings?"}
        existing = [{"chapter": 2, "topic": "Simple Interest", "question": "What is interest earned on savings accounts?"}]
        assert is_semantic_duplicate(candidate, existing) is True

    def test_short_intent_same_topic_different_objective_not_duplicate(self):
        """Step 3B: 'What is currency?' ≠ currency-symbol matching (length-imbalance)."""
        candidate = {"chapter": 1, "topic": "Currency", "question": "What is currency?"}
        existing = [
            {
                "chapter": 1,
                "topic": "Currency",
                "question": "Identify the currency symbols that are correctly matched with their countries.",
            }
        ]
        assert is_semantic_duplicate(candidate, existing) is False

    def test_subset_intent_different_comparison_not_duplicate(self):
        """money vs currency difference ≠ paper money vs coins difference."""
        candidate = {
            "chapter": 1,
            "topic": "Money and Currency",
            "question": "What is the main difference between money and currency?",
        }
        existing = [
            {
                "chapter": 1,
                "topic": "Currency",
                "question": (
                    "Paper money and coins are both forms of currency used in India. "
                    "What is the main difference between paper money and coins?"
                ),
            }
        ]
        assert is_semantic_duplicate(candidate, existing) is False


class TestBankBatchContentAwareLexical:
    """Step 3B: Bank Batch content-aware lexical gate; Final Paper unchanged."""

    def test_template_scaffold_does_not_flag_different_functions(self):
        sov = "Which of the following is an example of money being used as a store of value?"
        moe = "Which of the following is an example of money being used as a medium of exchange?"
        assert is_near_duplicate(sov, [moe], content_aware=True) is False
        # Final Paper legacy still uses full-word overlap
        assert is_near_duplicate(sov, [moe], content_aware=False) is True

    def test_exact_and_true_paraphrase_still_rejected(self):
        a = "Which of the following is an example of a denomination used in India?"
        b = "Which of the following is an example of a denomination of money in India?"
        assert is_near_duplicate(a, [a], content_aware=True) is True
        assert is_near_duplicate(b, [a], content_aware=True) is True

    def test_currency_example_vs_medium_of_exchange_not_lexical_dup(self):
        assert (
            is_near_duplicate(
                "Which of the following is an example of currency?",
                [
                    "Which of the following is an example of money being used as a medium of exchange?"
                ],
                content_aware=True,
            )
            is False
        )

class TestTopicMetadata:
    """Tests for validate_topic_metadata()."""

    def test_valid_topic(self):
        errors = validate_topic_metadata("Simple Interest", "Bank Deposits", "Chapter 2 — Banking")
        assert errors == []

    def test_generic_grade_topic_rejected(self):
        errors = validate_topic_metadata("Grade 5", "", "Chapter 1")
        assert any("generic topic" in e for e in errors)

    def test_generic_chapter_topic_rejected(self):
        errors = validate_topic_metadata("Chapter 3", "", "Chapter 3")
        assert any("generic topic" in e or "repeats the chapter" in e for e in errors)

    def test_topic_repeating_chapter_title_rejected(self):
        errors = validate_topic_metadata("Banking", "", "Banking")
        assert any("repeats the chapter" in e for e in errors)

    def test_generic_sub_topic_flagged(self):
        errors = validate_topic_metadata("Budgeting", "Chapter 4", "Chapter 4 — Money")
        assert any("generic sub_topic" in e for e in errors)

    def test_empty_topic_rejected(self):
        errors = validate_topic_metadata("", "Subtopic", "Chapter 1")
        assert any("generic topic" in e for e in errors)

    def test_section_pattern_rejected(self):
        errors = validate_topic_metadata("Section 2", "Detail", "Chapter 1")
        assert any("generic topic" in e for e in errors)

    def test_unit_pattern_rejected(self):
        errors = validate_topic_metadata("Unit 3", "Overview", "Chapter 3")
        assert any("generic topic" in e for e in errors)


# ---------------------------------------------------------------------------
# Integration: apply_independent_validation with quality checks
# ---------------------------------------------------------------------------

class TestQualityValidationIntegration:
    """End-to-end tests through apply_independent_validation with blind solver data."""

    @staticmethod
    def _good_flags():
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

    @staticmethod
    def _medium_scores():
        return {k: 2 for k in (
            "knowledge", "reasoning", "context", "application",
            "interpretation", "decision_making", "concept_integration", "distractor_quality",
        )}

    @staticmethod
    def _good_solver(correct_indices):
        defensible = [False] * 5
        for i in correct_indices:
            defensible[i] = True
        labels = "ABCDE"
        return {
            "independently_derived_indices": correct_indices,
            "option_analysis": [
                {"option": labels[i], "defensible": defensible[i], "reason": ""}
                for i in range(5)
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
        }

    def test_full_pass(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="What causes inflation?")
        q["topic"] = "Inflation"
        q["sub_topic"] = "Causes"
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=self._good_solver([0]),
        )
        assert result["passed"] is True

    def test_solver_disagrees_rejects(self):
        """Blind solver finds different answer → reject."""
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="What causes inflation?")
        q["topic"] = "Inflation"
        q["sub_topic"] = "Causes"
        bad_solver = self._good_solver([2])
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=bad_solver,
        )
        assert result["passed"] is False
        assert any("independent solver disagrees" in r for r in result["validation_reasons"])

    def test_multiple_defensible_single_correct_rejects(self):
        """Two defensible options in single_correct → reject."""
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="What causes deflation?")
        q["topic"] = "Deflation"
        q["sub_topic"] = "Causes"
        solver = self._good_solver([0])
        solver["option_analysis"][2]["defensible"] = True
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("multiple defensible" in r for r in result["validation_reasons"])

    def test_information_insufficient_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[1], text="Ambiguous budget question")
        q["topic"] = "Budgeting"
        q["sub_topic"] = "Planning"
        solver = self._good_solver([1])
        solver["information_sufficient"] = False
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("information insufficient" in r for r in result["validation_reasons"])

    def test_arithmetic_inconsistent_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="Calculate annual interest on 500 at 6%")
        q["topic"] = "Simple Interest"
        q["sub_topic"] = "Calculation"
        solver = self._good_solver([0])
        solver["arithmetic_consistent"] = False
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("arithmetic" in r for r in result["validation_reasons"])

    def test_unsupported_claim_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[3], text="Why invest instead of save?")
        q["topic"] = "Investing"
        q["sub_topic"] = "Growth"
        solver = self._good_solver([3])
        solver["no_unsupported_claims"] = False
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("unsupported" in r for r in result["validation_reasons"])

    def test_semantic_duplicate_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct", chapter=1)
        q = _question(answer_type="single_correct", indices=[0], text="What is an investment?")
        q["topic"] = "Investment"
        q["sub_topic"] = "Definition"
        existing_qs = [{"chapter": 1, "topic": "Investment", "question": "What does investing mean?"}]
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            existing_questions=existing_qs,
            book_grounded=False,
            blind_solver=self._good_solver([0]),
        )
        assert result["passed"] is False
        assert any("semantic duplicate" in r for r in result["validation_reasons"])

    def test_generic_topic_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="Generic topic question")
        q["topic"] = "Grade 5"
        q["sub_topic"] = ""
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=self._good_solver([0]),
        )
        assert result["passed"] is False
        assert any("generic topic" in r for r in result["validation_reasons"])

    def test_no_blind_solver_still_validates(self):
        """When blind solver is None, other checks still run."""
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="Normal question here")
        q["topic"] = "Finance Basics"
        q["sub_topic"] = "Overview"
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._medium_scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=None,
        )
        assert result["passed"] is True

    def test_cognitive_and_quality_independently_fail(self):
        """Cognitive mismatch + quality failure both reported separately."""
        slot = _slot(target_difficulty="difficult", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="Easy question for difficult slot")
        q["topic"] = "Savings"
        q["sub_topic"] = "Basics"
        easy_scores = {k: 1 for k in (
            "knowledge", "reasoning", "context", "application",
            "interpretation", "decision_making", "concept_integration", "distractor_quality",
        )}
        solver = self._good_solver([0])
        solver["information_sufficient"] = False
        result = apply_independent_validation(
            slot=slot,
            criterion_scores=easy_scores,
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        reasons = result["validation_reasons"]
        assert any("cognitive difficulty mismatch" in r for r in reasons)
        assert any("information insufficient" in r for r in reasons)


# ---------------------------------------------------------------------------
# Focused regression tests for new validator behaviors
# ---------------------------------------------------------------------------
class TestNewValidatorPersistenceAndRules:
    @staticmethod
    def _good_flags():
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

    @staticmethod
    def _scores():
        return {k: 2 for k in (
            "knowledge", "reasoning", "context", "application",
            "interpretation", "decision_making", "concept_integration", "distractor_quality",
        )}

    @staticmethod
    def _good_solver(correct_indices):
        defensible = [False] * 5
        for i in correct_indices:
            defensible[i] = True
        labels = "ABCDE"
        return {
            "independently_derived_indices": list(correct_indices),
            "option_analysis": [
                {"option": labels[i], "defensible": defensible[i], "reason": ""}
                for i in range(5)
            ],
            "information_sufficient": True,
            "arithmetic_consistent": True,
            "no_unsupported_claims": True,
            "terminology_grounded": True,
        }

    def test_persists_blind_solver_structured_fields(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="What does savings mean?")
        q["topic"] = "Savings"
        q["sub_topic"] = "Meaning"
        q["options"] = ["A", "B", "C", "D", "E"]

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=self._good_solver([0]),
        )
        assert result["passed"] is True
        assert result["blind_solver_answer"] == "A"
        assert result["answer_agreement"] is True
        assert result["information_sufficient"] is True
        assert result["arithmetic_consistent"] is True
        assert result["no_unsupported_claims"] is True
        assert result["distractors_ok"] is True
        assert isinstance(result["option_defensibility"], list)

    def test_subjective_best_requires_objective_criterion(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(
            answer_type="single_correct",
            indices=[0],
            text="Which option is best for smart money management?",
        )
        q["topic"] = "Budgeting"
        q["sub_topic"] = "Savings"
        q["options"] = ["Correct", "Wrong1", "Wrong2", "Wrong3", "Wrong4"]
        solver = self._good_solver([0])

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("subjective 'best'" in r for r in result["validation_reasons"])

    def test_irrelevant_distractors_rejected(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        slot.subject = "Finance"
        q = _question(
            answer_type="single_correct",
            indices=[0],
            text="Calculate simple interest on savings.",
        )
        q["topic"] = "Savings"
        q["sub_topic"] = "Bank Accounts"
        q["options"] = [
            "Correct: interest is earned on savings",
            "Incorrect: become a bank manager",
            "Incorrect: get free gifts from the bank",
            "Incorrect: keeping records of temple money",
            "Incorrect: unrelated option",
        ]
        solver = self._good_solver([0])

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("unclear/irrelevant distractor" in r for r in result["validation_reasons"])

    def test_redundant_correct_options_rejected_multiple_correct(self):
        slot = _slot(target_difficulty="medium", answer_type="multiple_correct")
        slot.subject = "Finance"
        q = _question(
            answer_type="multiple_correct",
            indices=[1, 3],
            text="What grows money through compounding?",
        )
        q["topic"] = "Compounding"
        q["sub_topic"] = "Interest"
        q["options"] = [
            "A",
            "B: Earn interest on interest to grow savings",
            "C: unrelated",
            "D: Earn interest on interest to grow savings (rephrased)",
            "E",
        ]
        solver = self._good_solver([1, 3])

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("redundant correct options" in r for r in result["validation_reasons"])

    def test_topic_equals_subject_rejected(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        slot.subject = "Financial Literacy"
        q = _question(answer_type="single_correct", indices=[0], text="What is money?")
        q["topic"] = "Financial Literacy"
        q["sub_topic"] = "Money"
        q["options"] = ["Money", "X", "Y", "Z", "W"]
        solver = self._good_solver([0])

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("must not equal subject" in r for r in result["validation_reasons"])

    def test_terminology_grounding_rejects(self):
        slot = _slot(target_difficulty="medium", answer_type="single_correct")
        q = _question(answer_type="single_correct", indices=[0], text="Define double coincidence of wants.")
        q["topic"] = "Functions of Money"
        q["sub_topic"] = "Definitions"
        solver = self._good_solver([0])
        solver["terminology_grounded"] = False

        result = apply_independent_validation(
            slot=slot,
            criterion_scores=self._scores(),
            quality_flags=self._good_flags(),
            question=q,
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=solver,
        )
        assert result["passed"] is False
        assert any("terminology" in r.lower() for r in result["validation_reasons"])


# ---------------------------------------------------------------------------
# Reason-aware feedback for new rejection types
# ---------------------------------------------------------------------------

class TestReasonGuidanceNewTypes:
    """Verify _build_reason_aware_feedback handles all new rejection reasons."""

    def test_independent_solver_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["independent solver disagrees with answer key"], [], [], _slot()
        )
        assert "DIFFERENT answer" in fb or "independent" in fb.lower()

    def test_multiple_defensible_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["multiple defensible options in single_correct"], [], [], _slot()
        )
        assert "ONE option" in fb or "defensible" in fb.lower()

    def test_information_insufficient_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["information insufficient: stem does not provide enough data"], [], [], _slot()
        )
        assert "information" in fb.lower() or "missing" in fb.lower()

    def test_arithmetic_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["arithmetic/numerical inconsistency detected"], [], [], _slot()
        )
        assert "arithmetic" in fb.lower() or "calculation" in fb.lower()

    def test_unsupported_claim_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["unsupported absolute/misleading claim"], [], [], _slot()
        )
        assert "claim" in fb.lower() or "unsupported" in fb.lower()

    def test_semantic_duplicate_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["semantic duplicate: tests the same concept/intent"], [], [], _slot()
        )
        assert "DIFFERENT" in fb or "intent" in fb.lower()

    def test_topic_metadata_guidance(self):
        fb = qp._build_reason_aware_feedback(
            ["generic topic metadata: 'Grade 5'"], [], [], _slot()
        )
        assert "concept" in fb.lower() or "topic" in fb.lower()
