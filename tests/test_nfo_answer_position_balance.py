"""Bank Batch randomized answer-position balancing. Offline; no live LLM."""

from __future__ import annotations

import inspect
import random

from open_notebook.graphs import question_bank_batch as qbb
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_answer_pattern import (
    apply_answer_position_audit,
    apply_index_permutation,
    needs_randomized_position_balance,
    position_distribution,
    validate_post_shuffle,
)
from open_notebook.graphs.question_paper_blueprint import (
    apply_independent_validation,
    evaluate_blind_solver,
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


class TestNeedsBalance:
    def test_four_identical_needs_balance(self):
        assert needs_randomized_position_balance(["A", "A", "A", "A"]) is True

    def test_three_consecutive_needs_balance(self):
        assert needs_randomized_position_balance(["A", "A", "A", "B", "C"]) is True

    def test_skewed_interleaved_needs_balance(self):
        # 7 A of 10 — not a consecutive-4 pattern, still biased
        seq = ["A", "B", "A", "C", "A", "A", "D", "A", "E", "A"]
        assert seq.count("A") == 6
        assert needs_randomized_position_balance(seq) is True

    def test_irregular_natural_does_not_need_balance(self):
        assert needs_randomized_position_balance(["A", "B", "A", "D", "C", "A"]) is False

    def test_small_n_does_not_need_balance(self):
        assert needs_randomized_position_balance(["A", "A", "B"]) is False


class TestRandomizedBalance:
    def test_skewed_batch_is_rebalanced(self):
        # A A B A C A D A E A — 6/10 A
        letters = [0, 0, 1, 0, 2, 0, 3, 0, 4, 0]
        qs = [
            _q(i + 1, correct=letters[i], expl=f"{_opts()[letters[i]]} is taught.")
            for i in range(10)
        ]
        out, diag = apply_answer_position_audit(qs, rng=random.Random(7))
        assert diag["answer_position_before"] == ["A", "A", "B", "A", "C", "A", "D", "A", "E", "A"]
        assert diag["distribution_before"]["A"] == 6
        after = diag["answer_position_after"]
        dist = diag["distribution_after"]
        singles = [q for q in out if q.get("answer_type") == "single_correct"]
        assert after == ["ABCDE"[int(q["correct_indices"][0])] for q in singles]
        assert max(dist.values()) <= 3
        assert needs_randomized_position_balance(after) is False
        assert diag["accepted_count"] == 10
        assert len(out) == 10
        assert diag["position_balance_applied"] is True

    def test_not_a_fixed_abcde_pattern(self):
        letters = [0] * 10
        qs = [_q(i + 1, correct=0, expl="Alpha is taught.") for i in range(10)]
        sequences = []
        for seed in range(8):
            out, diag = apply_answer_position_audit(qs, rng=random.Random(seed))
            sequences.append(tuple(diag["answer_position_after"]))
        assert len(set(sequences)) > 1
        assert ("A", "B", "C", "D", "E", "A", "B", "C", "D", "E") not in sequences

    def test_preserves_stem_option_meanings_and_correct_text(self):
        qs = [
            _q(
                i + 1,
                correct=0,
                expl="Alpha is taught.",
                options=["Keep-A", "Keep-B", "Keep-C", "Keep-D", "Keep-E"],
            )
            for i in range(8)
        ]
        out, diag = apply_answer_position_audit(qs, rng=random.Random(3))
        assert [q["question"] for q in out] == [q["question"] for q in qs]
        for before, after in zip(qs, out):
            assert validate_post_shuffle(before, after) == ""
            old_correct = before["options"][before["correct_indices"][0]]
            new_correct = after["options"][after["correct_indices"][0]]
            assert old_correct == new_correct == "Keep-A"
            assert sorted(after["options"]) == sorted(before["options"])

    def test_explanation_letter_mapping_updated(self):
        q = _q(1, correct=0, expl="Option A is correct because Alpha is taught.")
        qs = [q] + [_q(i, correct=0, expl="Alpha is taught.") for i in range(2, 8)]
        out, _ = apply_answer_position_audit(qs, rng=random.Random(1))
        first = next(x for x in out if x["question_number"] == 1)
        idx = first["correct_indices"][0]
        letter = "ABCDE"[idx]
        if idx != 0:
            assert f"Option {letter} is correct" in first["explanation"]
            assert "Option A is correct" not in first["explanation"]
        assert first["options"][idx] == "Alpha"

    def test_unsafe_explanation_is_skipped_not_rewritten(self):
        qs = [
            _q(i, correct=0, expl="See column B of the table in the chapter.")
            for i in range(1, 8)
        ]
        out, diag = apply_answer_position_audit(qs, rng=random.Random(2))
        assert diag["questions_skipped_unsafe"]
        assert all(q["correct_indices"] == [0] for q in out)
        assert all(q["explanation"].startswith("See column B") for q in out)

    def test_natural_mix_is_left_alone(self):
        letters = [0, 1, 0, 3, 2, 0]
        qs = [_q(i, correct=letters[i - 1], expl="Taught.") for i in range(1, 7)]
        out, diag = apply_answer_position_audit(qs, rng=random.Random(0))
        assert diag["pattern_detected"] is False
        assert diag["position_balance_applied"] is False
        assert diag["answer_position_before"] == diag["answer_position_after"]
        assert [x["correct_indices"] for x in out] == [q["correct_indices"] for q in qs]

    def test_diagnostics_keys_present(self):
        qs = [_q(i, correct=0, expl="Alpha is taught.") for i in range(1, 6)]
        _, diag = apply_answer_position_audit(qs, rng=random.Random(4))
        assert "answer_position_before" in diag
        assert "answer_position_after" in diag
        assert "distribution_before" in diag
        assert "distribution_after" in diag
        assert set(diag["distribution_before"]) == set("ABCDE")
        assert set(diag["distribution_after"]) == set("ABCDE")

    def test_multiple_correct_not_required_for_single_balance(self):
        singles = [_q(i, correct=0, expl="Alpha is taught.") for i in range(1, 6)]
        multi = _q(
            6,
            atype="multiple_correct",
            correct=[1, 2],
            expl="Bravo and Charlie are taught.",
        )
        out, diag = apply_answer_position_audit(singles + [multi], rng=random.Random(5))
        m = next(q for q in out if q["question_number"] == 6)
        assert sorted(m["options"][i] for i in m["correct_indices"]) == ["Bravo", "Charlie"]
        assert diag["accepted_count"] == 6


class TestBankBatchOnlyAndUnchangedNeighbors:
    def test_hook_is_audit_not_generation_or_final_paper(self):
        fill_src = inspect.getsource(qp.fill_slots)
        refill_src = inspect.getsource(qp.refill_slots)
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "apply_answer_position_audit" not in fill_src
        assert "apply_answer_position_audit" not in refill_src
        assert "balance answer" not in gen_src.lower()
        assert "apply_answer_position_audit" in inspect.getsource(qbb.audit_bank_batch_node)
        assert "apply_answer_position_audit" not in inspect.getsource(qp.audit_assembled_paper)
        persist = inspect.getsource(qbb.persist_bank_batch)
        assert "apply_answer_position_audit" not in persist
        graph_src = inspect.getsource(qbb.build_question_bank_batch_graph)
        assert graph_src.index("audit_bank_batch") < graph_src.index("persist_bank_batch")

    def test_validators_and_bands_untouched(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        assert evaluate_blind_solver(None, [0], "single_correct") == []
        _ = apply_independent_validation
        assert "ChatOpenAI" not in inspect.getsource(apply_answer_position_audit)
