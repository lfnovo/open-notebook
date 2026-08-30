"""Yield optimization: academic failure-family intent retirement + saturation.

Validators, thresholds, retry limits, and length recovery must remain unchanged.
"""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_BLIND_ANSWER,
    FAILURE_FAMILY_COGNITIVE,
    FAILURE_FAMILY_DISTRACTOR,
    FAILURE_FAMILY_GRADE,
    FAILURE_FAMILY_GROUNDING,
    FAILURE_FAMILY_SUBJECTIVE_BEST,
    INTENT_DUPLICATE_HITS_BEFORE_RETIRE,
    INTENT_FAMILY_HITS_BEFORE_RETIRE,
    apply_academic_failure_intent_policy,
    classify_academic_failure_family,
    empty_intent_diagnostics,
    intent_concept_usage_count,
    take_next_unused_intent,
)
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    map_cognitive_score,
)


def _intent(iid="i1", concept="Commodity money", objective="Identify commodity money", form="recall a taught fact"):
    return {
        "intent_id": iid,
        "concept": concept,
        "objective": objective,
        "cognitive_form": form,
        "topic": concept,
        "sub_topic": objective,
        "chunk_index": 0,
    }


class TestAcademicFailureFamilyClassification:
    def test_distractor_family(self):
        assert (
            classify_academic_failure_family(["unclear/irrelevant distractor(s): C"])
            == FAILURE_FAMILY_DISTRACTOR
        )

    def test_cognitive_family(self):
        assert (
            classify_academic_failure_family(
                ["cognitive difficulty mismatch: target=easy, validated=medium (score=15)"]
            )
            == FAILURE_FAMILY_COGNITIVE
        )

    def test_subjective_best_family(self):
        assert (
            classify_academic_failure_family(
                ["subjective 'best' question lacks an explicit objective decision criterion"]
            )
            == FAILURE_FAMILY_SUBJECTIVE_BEST
        )

    def test_grounding_family(self):
        assert (
            classify_academic_failure_family(
                ["not grounded in the supplied chapter content (possible hallucination)"]
            )
            == FAILURE_FAMILY_GROUNDING
        )

    def test_grade_family(self):
        assert (
            classify_academic_failure_family(
                ["not appropriate for the selected grade"]
            )
            == FAILURE_FAMILY_GRADE
        )

    def test_blind_answer_family(self):
        assert (
            classify_academic_failure_family(
                ["independent solver disagrees with marked answers"]
            )
            == FAILURE_FAMILY_BLIND_ANSWER
        )

    def test_distractor_and_cognitive_are_separate(self):
        d = classify_academic_failure_family(["unclear/irrelevant distractor(s): B"])
        c = classify_academic_failure_family(
            ["cognitive difficulty mismatch: target=easy, validated=medium (score=13)"]
        )
        assert d == FAILURE_FAMILY_DISTRACTOR
        assert c == FAILURE_FAMILY_COGNITIVE
        assert d != c

    def test_length_and_provider_do_not_count(self):
        assert classify_academic_failure_family(
            ["Generation failed; rewrite a complete MCQ with five options A–E."]
        ) is None
        assert classify_academic_failure_family(
            ["AI service error: length limit was reached"]
        ) is None

    def test_duplicate_does_not_use_academic_family(self):
        assert (
            classify_academic_failure_family(
                ["duplicate or near-duplicate of an existing question"]
            )
            is None
        )


class TestAcademicFailureIntentRetirement:
    def _policy(self, family, hits_state, active, remaining, diagnostics=None):
        return apply_academic_failure_intent_policy(
            active_intent=active,
            failure_family=family,
            intent_family_hits=hits_state,
            intent_retired_ids=set(),
            intent_remaining=remaining,
            intent_assignments={"1": active},
            slot_key="1",
            intent_diagnostics=diagnostics if diagnostics is not None else empty_intent_diagnostics(),
            target_difficulty="easy",
            usage_questions=[],
        )

    def test_first_distractor_keeps_intent(self):
        active = _intent()
        remaining = [_intent("i2", concept="Fiat money", objective="Define fiat money")]
        hits: dict = {}
        nxt, fb, retired = self._policy(
            FAILURE_FAMILY_DISTRACTOR, hits, active, remaining
        )
        assert retired is False
        assert nxt is active
        assert nxt["intent_id"] == "i1"
        assert "INTENT RETRY (distractor)" in fb
        assert hits["i1"][FAILURE_FAMILY_DISTRACTOR] == 1

    def test_second_distractor_retires_intent(self):
        active = _intent()
        replacement = _intent("i2", concept="Fiat money", objective="Define fiat money")
        remaining = [replacement]
        hits: dict = {}
        diag = empty_intent_diagnostics()
        nxt1, _, retired1 = self._policy(
            FAILURE_FAMILY_DISTRACTOR, hits, active, remaining, diag
        )
        assert retired1 is False
        nxt2, fb2, retired2 = apply_academic_failure_intent_policy(
            active_intent=nxt1,
            failure_family=FAILURE_FAMILY_DISTRACTOR,
            intent_family_hits=hits,
            intent_retired_ids=set(),
            intent_remaining=remaining,
            intent_assignments={"1": nxt1},
            slot_key="1",
            intent_diagnostics=diag,
            target_difficulty="easy",
            usage_questions=[],
        )
        assert retired2 is True
        assert nxt2 is not None
        assert nxt2["intent_id"] == "i2"
        assert "INTENT RETIRED" in fb2
        assert int(diag["intents_retired_after_academic_failure"]) == 1
        assert diag["academic_failure_events"][-1]["retired"] is True

    def test_repeated_cognitive_retires(self):
        active = _intent()
        remaining = [_intent("i2", concept="Barter", objective="Recall barter")]
        hits: dict = {}
        retired_ids: set = set()
        diag = empty_intent_diagnostics()
        for _ in range(2):
            active, _fb, retired = apply_academic_failure_intent_policy(
                active_intent=active,
                failure_family=FAILURE_FAMILY_COGNITIVE,
                intent_family_hits=hits,
                intent_retired_ids=retired_ids,
                intent_remaining=remaining,
                intent_assignments={"1": active},
                slot_key="1",
                intent_diagnostics=diag,
                target_difficulty="easy",
            )
        assert retired is True
        assert "i1" in retired_ids

    def test_repeated_subjective_best_retires(self):
        active = _intent()
        remaining = [_intent("i2", concept="Savings", objective="Define savings")]
        hits: dict = {}
        retired_ids: set = set()
        for _ in range(2):
            active, _, retired = apply_academic_failure_intent_policy(
                active_intent=active,
                failure_family=FAILURE_FAMILY_SUBJECTIVE_BEST,
                intent_family_hits=hits,
                intent_retired_ids=retired_ids,
                intent_remaining=remaining,
                intent_assignments={"1": active},
                slot_key="1",
                intent_diagnostics=empty_intent_diagnostics(),
                target_difficulty="easy",
            )
        assert retired is True

    def test_repeated_grounding_retires(self):
        active = _intent()
        remaining = [_intent("i2", concept="Budget", objective="Define budget")]
        hits: dict = {}
        retired_ids: set = set()
        for _ in range(2):
            active, _, retired = apply_academic_failure_intent_policy(
                active_intent=active,
                failure_family=FAILURE_FAMILY_GROUNDING,
                intent_family_hits=hits,
                intent_retired_ids=retired_ids,
                intent_remaining=remaining,
                intent_assignments={"1": active},
                slot_key="1",
                intent_diagnostics=empty_intent_diagnostics(),
            )
        assert retired is True

    def test_repeated_grade_retires(self):
        active = _intent()
        remaining = [_intent("i2", concept="Cash", objective="Define cash")]
        hits: dict = {}
        retired_ids: set = set()
        for _ in range(2):
            active, _, retired = apply_academic_failure_intent_policy(
                active_intent=active,
                failure_family=FAILURE_FAMILY_GRADE,
                intent_family_hits=hits,
                intent_retired_ids=retired_ids,
                intent_remaining=remaining,
                intent_assignments={"1": active},
                slot_key="1",
                intent_diagnostics=empty_intent_diagnostics(),
            )
        assert retired is True

    def test_repeated_blind_answer_retires(self):
        active = _intent()
        remaining = [_intent("i2", concept="Cheque", objective="Define cheque")]
        hits: dict = {}
        retired_ids: set = set()
        for _ in range(2):
            active, _, retired = apply_academic_failure_intent_policy(
                active_intent=active,
                failure_family=FAILURE_FAMILY_BLIND_ANSWER,
                intent_family_hits=hits,
                intent_retired_ids=retired_ids,
                intent_remaining=remaining,
                intent_assignments={"1": active},
                slot_key="1",
                intent_diagnostics=empty_intent_diagnostics(),
            )
        assert retired is True

    def test_distractor_plus_cognitive_separate_counters(self):
        active = _intent()
        remaining = [_intent("i2", concept="Fiat", objective="Define fiat")]
        hits: dict = {}
        retired_ids: set = set()
        diag = empty_intent_diagnostics()
        a1, _, r1 = apply_academic_failure_intent_policy(
            active_intent=active,
            failure_family=FAILURE_FAMILY_DISTRACTOR,
            intent_family_hits=hits,
            intent_retired_ids=retired_ids,
            intent_remaining=remaining,
            intent_assignments={"1": active},
            slot_key="1",
            intent_diagnostics=diag,
        )
        a2, _, r2 = apply_academic_failure_intent_policy(
            active_intent=a1,
            failure_family=FAILURE_FAMILY_COGNITIVE,
            intent_family_hits=hits,
            intent_retired_ids=retired_ids,
            intent_remaining=remaining,
            intent_assignments={"1": a1},
            slot_key="1",
            intent_diagnostics=diag,
        )
        assert r1 is False and r2 is False
        assert a2["intent_id"] == "i1"
        assert hits["i1"][FAILURE_FAMILY_DISTRACTOR] == 1
        assert hits["i1"][FAILURE_FAMILY_COGNITIVE] == 1
        assert "i1" not in retired_ids

    def test_threshold_is_two(self):
        assert INTENT_FAMILY_HITS_BEFORE_RETIRE == 2
        assert INTENT_DUPLICATE_HITS_BEFORE_RETIRE == 2


class TestSaturationAwareSelection:
    def test_prefers_underrepresented_concept(self):
        remaining = [
            _intent("sat", concept="UPI", objective="Recall UPI features"),
            _intent("fresh", concept="EMI", objective="Recall EMI variables"),
        ]
        usage = [
            {"topic": "UPI", "assigned_concept": "UPI"},
            {"topic": "UPI", "question": "What is UPI?"},
            {"topic": "UPI"},
        ]
        diag = empty_intent_diagnostics()
        nxt = take_next_unused_intent(
            remaining,
            usage_questions=usage,
            diagnostics=diag,
            target_difficulty="easy",
        )
        assert nxt is not None
        assert nxt["intent_id"] == "fresh"
        assert int(diag.get("saturation_influenced_selections") or 0) >= 1

    def test_saturation_never_permanently_excludes(self):
        remaining = [
            _intent("only", concept="UPI", objective="Recall UPI features"),
        ]
        usage = [{"topic": "UPI"}] * 10
        nxt = take_next_unused_intent(
            remaining, usage_questions=usage, target_difficulty="easy"
        )
        assert nxt is not None
        assert nxt["intent_id"] == "only"

    def test_replacement_stays_easy_compatible(self):
        active = _intent()
        remaining = [
            {
                "intent_id": "unsafe",
                "cognitive_form": "identify a concept",
                "concept": "Diversification",
                "objective": "Identify how diversification protects value when one asset underperforms",
            },
            _intent("safe", concept="REITs", objective="Recall that REITs own property", form="recall a taught fact"),
        ]
        hits = {"i1": {FAILURE_FAMILY_DISTRACTOR: 1}}
        nxt, _, retired = apply_academic_failure_intent_policy(
            active_intent=active,
            failure_family=FAILURE_FAMILY_DISTRACTOR,
            intent_family_hits=hits,
            intent_retired_ids=set(),
            intent_remaining=remaining,
            intent_assignments={"1": active},
            slot_key="1",
            intent_diagnostics=empty_intent_diagnostics(),
            target_difficulty="easy",
            usage_questions=[],
        )
        assert retired is True
        assert nxt is not None
        assert nxt["intent_id"] == "safe"


class TestNonRegressionGuards:
    def test_easy_slot_contract_present(self):
        assert "one primary concept" in qp.BANK_BATCH_EASY_SLOT_CONTRACT.lower()
        assert "0–1" in qp.BANK_BATCH_EASY_SLOT_CONTRACT or "0-1" in qp.BANK_BATCH_EASY_SLOT_CONTRACT
        assert "best" in qp.BANK_BATCH_EASY_SLOT_CONTRACT.lower()
        assert "BANK_BATCH_EASY_SLOT_CONTRACT" in inspect.getsource(qp._generate_for_slot)

    def test_cognitive_thresholds_unchanged(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        src = inspect.getsource(map_cognitive_score)
        assert "total <= 12" in src
        assert "total <= 18" in src

    def test_retry_limits_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_duplicate_thresholds_unchanged(self):
        from open_notebook.graphs import question_paper_blueprint as bp

        src = open(bp.__file__, encoding="utf-8").read()
        assert "0.70" in src or "0.7" in src
        assert "0.75" in src

    def test_length_recovery_unchanged(self):
        assert qp.GENERATOR_LENGTH_RETRY_MAX_TOKENS == 4096
        assert "is_structured_output_length_error" in open(qp.__file__, encoding="utf-8").read()

    def test_blind_and_cognitive_still_invoked_in_validate_path(self):
        src = inspect.getsource(qp._validate_slot_independently)
        assert "_blind_solve" in src
        assert "_validate_cognitive_quality" in src

    def test_fill_still_runs_early_gates_then_validators(self):
        src = inspect.getsource(qp.fill_slots)
        assert "run_bank_batch_early_gates" in src
        assert "_validate_slot_independently" in src
        assert "apply_academic_failure_intent_policy" in src
        assert "apply_duplicate_intent_policy" in src

    def test_accepted_questions_never_regenerated_in_refill(self):
        src = inspect.getsource(qp.refill_slots)
        assert "never regenerate" in src.lower() or "Snapshot approved" in src

    def test_usage_count_helper(self):
        intent = _intent(concept="UPI")
        assert intent_concept_usage_count(intent, [{"topic": "UPI"}, {"topic": "EMI"}]) == 1
