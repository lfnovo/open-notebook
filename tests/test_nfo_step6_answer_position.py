"""NFO Step 6 — answer-position anti-pattern (offline; no live LLM)."""

import inspect

from open_notebook.graphs import question_bank_batch as qbb
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_answer_pattern import (
    apply_answer_position_audit,
    apply_index_permutation,
    detect_multiple_correct_set_pattern,
    detect_single_correct_position_pattern,
    validate_post_shuffle,
)
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    apply_independent_validation,
    evaluate_blind_solver,
    evaluate_mcq_structural_rules,
    evaluate_obvious_option_quality,
    evaluate_unnecessary_source_references,
    find_semantic_duplicate_match,
    is_near_duplicate,
    map_cognitive_score,
)


def _opts():
    return ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]


def _q(n, *, atype="single_correct", correct=0, expl="The taught fact is Alpha.", **extra):
    idx = correct if isinstance(correct, list) else [correct]
    rec = {
        "question_number": n,
        "question": f"Stem for question {n} about a taught concept?",
        "answer_type": atype,
        "options": list(_opts()),
        "correct_indices": list(idx),
        "answer": "",
        "explanation": expl,
        "validation_status": "passed",
        "target_difficulty": "easy",
        "validated_cognitive_difficulty": "easy",
        "chapter": 1,
        "grade": "9",
    }
    rec.update(extra)
    return rec


class TestNfoStep6AnswerPosition:
    def test_abcde_sequence_detected(self):
        qs = [_q(i, correct=i - 1) for i in range(1, 6)]
        det = detect_single_correct_position_pattern(qs)
        assert det["detected"] is True
        assert det["pattern_type"] in {"alphabetical_run", "question_number_determined"}
        assert det["sequence"] == ["A", "B", "C", "D", "E"]

    def test_abab_sequence_detected(self):
        qs = [_q(i, correct=(i - 1) % 2) for i in range(1, 5)]
        det = detect_single_correct_position_pattern(qs)
        assert det["detected"] is True
        assert det["pattern_type"] == "alternating_period_2"

    def test_excessive_same_answer_detected(self):
        qs = [_q(i, correct=0) for i in range(1, 5)]
        det = detect_single_correct_position_pattern(qs)
        assert det["detected"] is True
        assert det["pattern_type"] == "excessive_same_position"

    def test_natural_irregular_sequence_no_pattern(self):
        # User example: A, B, A, D, C, A
        letters = [0, 1, 0, 3, 2, 0]
        qs = [_q(i, correct=letters[i - 1]) for i in range(1, 7)]
        det = detect_single_correct_position_pattern(qs)
        assert det["detected"] is False

    def test_small_natural_repetition_does_not_overcorrect(self):
        qs = [_q(1, correct=0), _q(2, correct=0), _q(3, correct=2), _q(4, correct=4)]
        det = detect_single_correct_position_pattern(qs)
        assert det["detected"] is False
        out, diag = apply_answer_position_audit(qs)
        assert diag["pattern_detected"] is False
        assert diag["questions_safely_reordered"] == []
        assert [x["correct_indices"] for x in out] == [q["correct_indices"] for q in qs]

    def test_repeated_multiple_sets_detected(self):
        qs = [
            _q(i, atype="multiple_correct", correct=[0, 1], expl="Alpha and Bravo are taught.")
            for i in range(1, 4)
        ]
        det = detect_multiple_correct_set_pattern(qs)
        assert det["detected"] is True
        assert det["pattern_type"] == "repeated_answer_set"

    def test_varied_multiple_sets_no_pattern(self):
        qs = [
            _q(1, atype="multiple_correct", correct=[0, 1], expl="Taught pair one."),
            _q(2, atype="multiple_correct", correct=[1, 2, 3], expl="Taught triple."),
            _q(3, atype="multiple_correct", correct=[0, 3], expl="Taught pair two."),
        ]
        det = detect_multiple_correct_set_pattern(qs)
        assert det["detected"] is False

    def test_safe_single_shuffle_remaps_index(self):
        q = _q(1, correct=0, expl="Alpha is the taught definition.")
        updated, err = apply_index_permutation(q, [1, 0, 2, 3, 4])
        assert not err
        assert updated["correct_indices"] == [1]
        assert updated["options"][1] == "Alpha"
        assert sorted(updated["options"]) == sorted(_opts())
        assert validate_post_shuffle(q, updated) == ""

    def test_safe_multiple_shuffle_remaps_all_indices(self):
        q = _q(
            1,
            atype="multiple_correct",
            correct=[0, 2],
            expl="Alpha and Charlie are both taught.",
        )
        # rotate +1: 0->1, 1->2, 2->3, 3->4, 4->0
        updated, err = apply_index_permutation(q, [1, 2, 3, 4, 0])
        assert not err
        assert updated["correct_indices"] == [1, 3]
        assert {updated["options"][i] for i in updated["correct_indices"]} == {"Alpha", "Charlie"}

    def test_option_text_set_unchanged_after_shuffle(self):
        q = _q(1, correct=2)
        updated, _ = apply_index_permutation(q, [4, 3, 2, 1, 0])
        assert sorted(updated["options"]) == sorted(q["options"])
        assert updated["question"] == q["question"]

    def test_explanation_letters_skipped_unless_remappable(self):
        qs = [_q(i, correct=0, expl="See column B of the table in the chapter.") for i in range(1, 5)]
        out, diag = apply_answer_position_audit(qs)
        assert diag["pattern_detected"] is True
        assert all(item["reason"] == "unsafe_explanation_letters" for item in diag["questions_skipped_unsafe"])
        assert diag["questions_safely_reordered"] == []
        assert [x["correct_indices"] for x in out] == [[0], [0], [0], [0]]

        remappable = _q(1, correct=0, expl="Option A is correct because Alpha is taught.")
        updated, err = apply_index_permutation(remappable, [1, 0, 2, 3, 4])
        assert not err
        assert "Option B is correct" in updated["explanation"]
        assert updated["correct_indices"] == [1]

    def test_exactly_five_and_answer_counts_after_shuffle(self):
        single = _q(1, correct=3)
        u, _ = apply_index_permutation(single, [2, 3, 4, 0, 1])
        assert len(u["options"]) == 5
        assert len(u["correct_indices"]) == 1
        multi = _q(2, atype="multiple_correct", correct=[0, 1, 2], expl="Three taught facts.")
        u2, _ = apply_index_permutation(multi, [1, 2, 3, 4, 0])
        assert len(u2["options"]) == 5
        assert 2 <= len(u2["correct_indices"]) <= 4

    def test_abcde_audit_reorders_without_changing_count(self):
        qs = [_q(i, correct=i - 1) for i in range(1, 6)]
        out, diag = apply_answer_position_audit(qs)
        assert diag["accepted_count"] == 5
        assert len(out) == 5
        assert diag["pattern_detected"] is True
        assert diag["questions_safely_reordered"]
        assert detect_single_correct_position_pattern(out)["detected"] is False
        stems = [q["question"] for q in qs]
        assert [q["question"] for q in out] == stems

    def test_no_refill_or_generation_hooks(self):
        fill_src = inspect.getsource(qp.fill_slots)
        refill_src = inspect.getsource(qp.refill_slots)
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "apply_answer_position_audit" not in fill_src
        assert "apply_answer_position_audit" not in refill_src
        assert "make this answer" not in gen_src.lower()
        assert "balance answer letters" not in gen_src.lower()
        assert "apply_answer_position_audit" in inspect.getsource(qbb.audit_bank_batch_node)
        assert "apply_answer_position_audit" not in inspect.getsource(qp.audit_assembled_paper)
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_no_new_llm_and_steps_1_5_intact(self):
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["Cash", "Credit", "Barter", "Loan", "Tax"],
            correct_indices=[0],
            question_text="What is cash?",
        ) == []
        assert evaluate_unnecessary_source_references("In this chapter, what is cash?")
        assert evaluate_obvious_option_quality(
            {"options": ["A tax on a budget"] * 5, "correct_indices": [0]}
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
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        assert inspect.signature(is_near_duplicate).parameters["min_overlap"].default == 0.7
        assert (
            inspect.signature(find_semantic_duplicate_match)
            .parameters["intent_overlap_threshold"]
            .default
            == 0.75
        )
        from open_notebook.graphs.question_bank_intent import classify_variety_relation

        assert classify_variety_relation is not None
        assert "ChatOpenAI" not in inspect.getsource(apply_answer_position_audit)
        assert "class VarietyPlanner" not in inspect.getsource(qp)
        assert "apply_independent_validation" in inspect.getsource(qp)
        _ = apply_independent_validation
