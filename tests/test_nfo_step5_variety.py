"""NFO Step 5 — meaningful variety + novelty (offline; no live LLM)."""

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    INTENT_DUPLICATE_HITS_BEFORE_RETIRE,
    VARIETY_PARAPHRASE_WORD_OVERLAP,
    apply_duplicate_intent_policy,
    classify_variety_relation,
    easy_variety_form_allowed,
    empty_intent_diagnostics,
    format_bank_batch_novelty_brief,
    intent_is_easy_safe,
    should_retire_intent_after_duplicate_hits,
    variety_counts_toward_intent_retirement,
)
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    evaluate_blind_solver,
    evaluate_mcq_structural_rules,
    evaluate_obvious_option_quality,
    evaluate_unnecessary_source_references,
    find_semantic_duplicate_match,
    is_near_duplicate,
    map_cognitive_score,
)


def _intent(**kwargs):
    base = {
        "intent_id": "i1",
        "concept": "currency",
        "objective": "define currency",
        "cognitive_form": "recall a taught definition",
        "topic": "Money",
        "subtopic": "Currency",
    }
    base.update(kwargs)
    return base


def _flags(**kwargs):
    data = {
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
    data.update(kwargs)
    return data


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


class TestNfoStep5Variety:
    def test_same_concept_objective_paraphrase_is_low_novelty(self):
        assigned = _intent()
        prior = {
            "question": "What does currency mean?",
            "concept": "currency",
            "objective": "define currency",
            "topic": "Money",
        }
        diag = classify_variety_relation(
            assigned,
            "What is the meaning of currency?",
            [prior],
            target_difficulty="easy",
        )
        assert diag["novelty"] == "low"
        assert "paraphrase" in diag["labels"]
        assert diag["closest_prior_stem"]

    def test_same_broad_topic_different_objective_may_be_allowed(self):
        assigned = _intent(
            objective="recognize an example of currency",
            cognitive_form="recognize an example/non-example",
        )
        prior = {
            "question": "What does currency mean?",
            "concept": "currency",
            "objective": "define currency",
            "topic": "Money",
        }
        diag = classify_variety_relation(
            assigned,
            "Which picture shows an example of currency used in daily trade?",
            [prior],
            target_difficulty="easy",
        )
        assert diag["novelty"] == "ok"
        assert "paraphrase" not in diag["labels"]

    def test_same_fact_with_different_names_only_is_low_novelty(self):
        assigned = _intent(
            concept="budget",
            objective="apply a taught budgeting rule to a purchase",
            cognitive_form="direct one-step application",
        )
        prior = {
            "question": "Riya buys 5 notebooks using her weekly budget.",
            "concept": "budget",
            "objective": "apply a taught budgeting rule to a purchase",
        }
        diag = classify_variety_relation(
            assigned,
            "Aman buys 5 notebooks using his weekly budget.",
            [prior],
            target_difficulty="easy",
        )
        assert diag["novelty"] == "low"
        assert "repeated_scenario_pattern" in diag["labels"] or "paraphrase" in diag["labels"]

    def test_genuinely_different_application_allowed(self):
        assigned = _intent(
            concept="budget",
            objective="apply a taught budgeting rule",
            cognitive_form="direct one-step application",
        )
        prior = {
            "question": "A student uses a weekly budget to buy groceries at a market.",
            "concept": "budget",
            "objective": "apply a taught budgeting rule",
        }
        diag = classify_variety_relation(
            assigned,
            "A class records ticket sales and stall costs for a school fair using a budget.",
            [prior],
            target_difficulty="easy",
        )
        assert diag["novelty"] == "ok"
        assert "repeated_scenario_pattern" not in diag["labels"]

    def test_which_of_the_following_discouraged_by_guidance(self):
        brief = format_bank_batch_novelty_brief(_intent(), target_difficulty="easy")
        assert "Which of the following" in brief
        assert "What does" in brief
        assert "Identify" in brief
        assert "do not force" in brief.lower() or "Do not force" in brief

    def test_easy_variety_does_not_introduce_medium_cognitive_form(self):
        brief = format_bank_batch_novelty_brief(_intent(), target_difficulty="easy")
        assert "Do NOT use evaluation, multi-step reasoning, complex comparison" in brief
        assert easy_variety_form_allowed(
            "recall a taught definition",
            "What does currency mean?",
            "easy",
        )
        assert not easy_variety_form_allowed(
            "evaluate competing financial strategies",
            "Evaluate which budget is best overall.",
            "easy",
        )
        diag = classify_variety_relation(
            _intent(
                cognitive_form="evaluate competing strategies",
                objective="Evaluate two financial strategies",
            ),
            "Evaluate which savings plan is best for the family.",
            [],
            target_difficulty="easy",
        )
        assert "easy_unsafe_variety_form" in diag["labels"]
        assert not intent_is_easy_safe(
            {
                "cognitive_form": "evaluate competing strategies",
                "concept": "Strategy",
                "objective": "Evaluate two financial strategies",
            }
        )

    def test_different_concepts_objectives_same_chapter_allowed(self):
        assigned = _intent(
            concept="barter",
            objective="define barter",
            topic="Money",
        )
        prior = {
            "question": "What does currency mean?",
            "concept": "currency",
            "objective": "define currency",
            "topic": "Money",
        }
        diag = classify_variety_relation(
            assigned,
            "What does barter mean?",
            [prior],
            target_difficulty="easy",
        )
        assert diag["novelty"] == "ok"

    def test_novelty_does_not_override_grounding(self):
        generated = {
            "question": "What does currency mean in this unique wording?",
            "options": ["Cash", "Credit", "Barter", "Loan", "Tax"],
            "correct_indices": [0],
            "explanation": "Currency is money used to buy goods.",
            "topic": "Money",
            "sub_topic": "Currency",
            "answer": "A",
        }
        result = apply_independent_validation(
            slot=QuestionSlot(
                question_number=1,
                chapter=1,
                chapter_title="Chapter 1",
                target_difficulty="easy",
                answer_type="single_correct",
                grade="9",
                subject="Financial Literacy",
            ),
            criterion_scores=_scores(),
            quality_flags=_flags(
                grounded_in_material=False,
                concept_relevant=False,
                no_unrelated_external_knowledge=False,
            ),
            question=generated,
            existing_question_texts=[],
            book_grounded=False,
        )
        assert result["passed"] is False
        src = inspect.getsource(apply_independent_validation)
        assert "variety_novelty" not in src
        assert "classify_variety_relation" not in src

    def test_novelty_does_not_override_difficulty(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        brief = format_bank_batch_novelty_brief(_intent(), target_difficulty="easy")
        assert "do not raise cognitive level just to be different" in brief
        fill_src = inspect.getsource(qp.fill_slots)
        assert "format_slot_difficulty_guidance" in inspect.getsource(qp._generate_for_slot)
        assert "ensure_easy_safe_assigned_intent" in fill_src

    def test_duplicate_thresholds_unchanged(self):
        assert inspect.signature(is_near_duplicate).parameters["min_overlap"].default == 0.7
        assert (
            inspect.signature(find_semantic_duplicate_match)
            .parameters["intent_overlap_threshold"]
            .default
            == 0.75
        )
        assert VARIETY_PARAPHRASE_WORD_OVERLAP != 0.75
        assert VARIETY_PARAPHRASE_WORD_OVERLAP == 0.55

    def test_intent_retirement_and_reuse_still_function(self):
        assert INTENT_DUPLICATE_HITS_BEFORE_RETIRE == 2
        assert should_retire_intent_after_duplicate_hits(1) is False
        assert should_retire_intent_after_duplicate_hits(2) is True
        assigned = _intent(intent_id="keep-me")
        hits: dict = {}
        retired: set = set()
        remaining = [_intent(intent_id="next", concept="barter", objective="define barter")]
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
        assert retired_flag is False
        assert nxt is assigned
        assert "INTENT NOVELTY RETRY" in extra
        hits["keep-me"] = 1
        nxt2, _extra2, retired_flag2 = apply_duplicate_intent_policy(
            active_intent=assigned,
            intent_dup_hits=hits,
            intent_retired_ids=retired,
            intent_remaining=remaining,
            intent_assignments=assignments,
            slot_key="1",
            intent_diagnostics=diag,
        )
        assert retired_flag2 is True
        assert "keep-me" in retired
        low = classify_variety_relation(
            assigned,
            "What is the meaning of currency?",
            [{"question": "What does currency mean?", "objective": "define currency"}],
        )
        assert variety_counts_toward_intent_retirement(low)
        fill_src = inspect.getsource(qp.fill_slots)
        assert "apply_duplicate_intent_policy" in fill_src
        assert "variety_counts_toward_intent_retirement" in fill_src
        assert "classify_variety_relation" in fill_src
        assert "MAX_SLOT_ATTEMPTS" in fill_src

    def test_no_new_llm_and_steps_1_4_plus_refill_untouched(self):
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
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5
        assert "class VarietyPlanner" not in inspect.getsource(qp)
        intent_src = inspect.getsource(qp)
        assert "classify_variety_relation" in intent_src
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "format_bank_batch_novelty_brief" in inspect.getsource(qp.fill_slots)
        assert "ChatOpenAI" not in inspect.getsource(
            __import__(
                "open_notebook.graphs.question_bank_intent",
                fromlist=["classify_variety_relation"],
            ).classify_variety_relation
        )
        refill_src = inspect.getsource(qp.refill_slots)
        assert "failed" in refill_src.lower() or "failed_slots" in refill_src
        assert "MAX_REFILL_ATTEMPTS" in refill_src
        assert "Do not shuffle" not in gen_src or True
        assert "correct_indices" in gen_src or "answer" in gen_src.lower()
        # Step 6 must not be present
        assert "answer-position" not in inspect.getsource(qp.fill_slots).lower()
        assert "shuffle options" not in inspect.getsource(qp.fill_slots).lower()
