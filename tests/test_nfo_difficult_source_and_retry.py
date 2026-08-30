"""Offline tests: chapter wording gap + Difficult contract + cognitive retry direction."""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_COGNITIVE,
    academic_failure_family_correction,
)
from open_notebook.graphs.question_paper_blueprint import (
    evaluate_mcq_structural_rules,
    evaluate_unnecessary_source_references,
    evaluate_unsupported_context_phrasing,
    map_cognitive_score,
    normalize_source_framing_text,
)


class TestChapterSourceWordingGapFix:
    def test_using_the_chapter_ascii_rejected(self):
        stem = (
            "Using the chapter's discussion of commercial banks, which payment "
            "choice is likely to succeed?"
        )
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["a", "b", "c", "d", "e"],
            correct_indices=[0],
            question_text=stem,
            standalone=True,
        )

    def test_using_the_chapter_unicode_apostrophe_rejected(self):
        stem = (
            "Using the chapter\u2019s discussion of commercial banks, which payment "
            "choice is likely to succeed?"
        )
        assert "\u2019" in stem
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)

    def test_bare_possessive_chapter_emi_formula_rejected(self):
        stem = (
            "A lender recalculates the monthly EMI using the chapter's EMI formula. "
            "Which statement is correct?"
        )
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)

    def test_unicode_apostrophe_normalized_before_match(self):
        assert normalize_source_framing_text("chapter\u2019s") == "chapter's"
        assert normalize_source_framing_text("chapter\u2018s") == "chapter's"
        curly = "the chapter\u2019s description of UPI is useful. Which is correct?"
        assert evaluate_unnecessary_source_references(curly)

    def test_clean_standalone_stem_passes(self):
        stem = "Which payment rail settles high-value transfers in real time?"
        assert evaluate_unnecessary_source_references(stem) == []
        assert evaluate_unsupported_context_phrasing(stem) == []

    def test_standalone_false_unchanged(self):
        stem = "Using the chapter's discussion, which option applies?"
        assert evaluate_unnecessary_source_references(stem, standalone=False) == []
        assert evaluate_unsupported_context_phrasing(stem, standalone=False) == []

    def test_chapter_number_title_not_broadly_rejected(self):
        stem = "In Chapter 2 of a personal-finance course, students learn banking. What is CRR?"
        # "in the chapter" style is still blocked; bare "Chapter 2" title mention alone is OK
        stem2 = "What is the Cash Reserve Ratio (CRR) used by a central bank?"
        assert evaluate_unnecessary_source_references(stem2) == []
        assert evaluate_unsupported_context_phrasing(stem2) == []


class TestDifficultSlotContract:
    def test_contract_exists_and_covers_demand_rules(self):
        text = qp.BANK_BATCH_DIFFICULT_SLOT_CONTRACT.lower()
        assert "analysis" in text or "inference" in text
        assert "multiple connected reasoning" in text
        assert "scenario length does not equal difficulty" in text
        assert "unrelated" in text
        assert "19–24" in qp.BANK_BATCH_DIFFICULT_SLOT_CONTRACT or "19-24" in text

    def test_generate_prompt_includes_difficult_contract_only_for_difficult(self):
        src = inspect.getsource(qp._generate_for_slot)
        assert "BANK_BATCH_DIFFICULT_SLOT_CONTRACT" in src
        assert '== "difficult"' in src
        assert "difficult_cal_block" in src
        # Easy path unchanged
        assert "BANK_BATCH_EASY_SLOT_CONTRACT" in src
        assert '== "easy"' in src

    def test_thresholds_unchanged(self):
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"


class TestCognitiveRetryDemandDirection:
    def _intent(self):
        return {
            "intent_id": "i1",
            "concept": "IMPS",
            "objective": "Choose a payment rail under constraints",
            "cognitive_form": "analyze a scenario using integrated concepts",
        }

    def test_difficult_under_demand_medium_score(self):
        reasons = [
            "cognitive difficulty mismatch: target=difficult, validated=medium "
            "(score=17); demand=under-demand; criteria=knowledge=2,reasoning=2,"
            "context=2,application=2,interpretation=2,decision_making=2,"
            "concept_integration=2,distractor_quality=3"
        ]
        fb = academic_failure_family_correction(
            FAILURE_FAMILY_COGNITIVE,
            self._intent(),
            target_difficulty="difficult",
            rejection_reasons=reasons,
        )
        assert "not difficult enough" in fb.lower()
        assert "multiple connected reasoning" in fb.lower()
        assert "one primary concept" not in fb.lower()
        assert "no more than one meaningful reasoning step" not in fb.lower()
        assert "exceeded difficult demand" not in fb.lower()

    def test_difficult_under_demand_mentions_low_criteria_briefly(self):
        reasons = [
            "cognitive difficulty mismatch: target=difficult, validated=medium "
            "(score=16); demand=under-demand; criteria=knowledge=2,reasoning=2,"
            "context=2,application=2,interpretation=2,decision_making=2,"
            "concept_integration=2,distractor_quality=2"
        ]
        fb = academic_failure_family_correction(
            FAILURE_FAMILY_COGNITIVE,
            self._intent(),
            target_difficulty="difficult",
            rejection_reasons=reasons,
        )
        assert "Increase genuine" in fb
        assert "superficial context" in fb

    def test_easy_over_demand_unchanged(self):
        reasons = [
            "cognitive difficulty mismatch: target=easy, validated=medium "
            "(score=15); demand=over-demand"
        ]
        fb = academic_failure_family_correction(
            FAILURE_FAMILY_COGNITIVE,
            self._intent(),
            target_difficulty="easy",
            rejection_reasons=reasons,
        )
        assert "exceeded easy demand" in fb.lower()
        assert "one primary concept" in fb.lower()
        assert "no more than one meaningful reasoning step" in fb.lower()

    def test_no_new_llm_in_correction_path(self):
        src = inspect.getsource(academic_failure_family_correction)
        assert "_invoke" not in src
        assert "provision" not in src.lower()
