"""Post-generation evidence chunk re-selection (Bank Batch only).

Offline. Does not change validators, thresholds, Blind independence,
Cognitive scoring, acceptance, or Final Paper.
"""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    BANK_BATCH_BLIND_SNIPPET_MAX,
    BANK_BATCH_VALIDATOR_GROUNDING_MAX,
    BANK_BATCH_VALIDATOR_GROUNDING_MIN,
    QuestionSlot,
    VALIDATION_CHUNK_RESELECTION_EVENT_LIMIT,
    empty_bank_cost_diagnostics,
    empty_validation_chunk_reselection_diagnostics,
    generated_question_evidence_probe,
    record_validation_chunk_reselection,
    select_blind_solver_source_snippet,
    select_cognitive_source_window,
    select_validation_chunk_for_generated,
)


CHUNK_BARTER = (
    "Early societies used barter. Cowrie shells and salt were common mediums "
    "of exchange among villages before metal coins existed. "
    * 12
)
CHUNK_SEIGNIORAGE = (
    "Seigniorage is the profit a government earns from issuing currency. "
    "Minting coins and printing notes create seigniorage revenue. "
    * 12
)
CHUNK_QE = (
    "Central banks may use Quantitative Easing (QE) in a crisis. "
    "A Central Bank Digital Currency (CBDC) is issued by the central bank. "
    * 12
)
OTHER_CHAPTER = (
    "Foreign exchange reserves and capital account convertibility are later topics. "
    * 12
)


def _slot(chapter: int = 1) -> QuestionSlot:
    return QuestionSlot(
        question_number=1,
        chapter=chapter,
        chapter_title="Money",
        target_difficulty="easy",
        answer_type="single_correct",
        grade="9",
        subject="Financial Education",
    )


def _generated(**overrides):
    data = {
        "question": "How does a government earn seigniorage from issuing currency?",
        "options": [
            "A. By collecting seigniorage when minting coins",
            "B. By swapping cowrie shells",
            "C. By banning all notes",
            "D. By closing every bank",
            "E. By taxing only salt",
        ],
        "topic": "Seigniorage",
        "sub_topic": "Currency issue profit",
    }
    data.update(overrides)
    return data


class TestGeneratedQuestionEvidenceProbe:
    def test_includes_stem_options_topic_and_subtopic(self):
        probe = generated_question_evidence_probe(_generated())
        assert "seigniorage" in probe.lower()
        assert "currency issue profit" in probe.lower()
        assert "minting coins" in probe.lower()
        assert "cowrie shells" in probe.lower()


class TestSelectValidationChunk:
    def test_reselects_better_matching_chapter_chunk(self):
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_SEIGNIORAGE],
            _generated(),
            original_index=0,
        )
        assert out["original_chunk_index"] == 0
        assert out["selected_validation_chunk_index"] == 1
        assert out["chunk_changed"] is True
        assert out["match_score"] > out["original_score"]
        assert out["reason"] == "reselected_higher_hits"
        assert "seigniorage" in out["excerpt"].lower()
        assert "barter" not in out["excerpt"].lower()

    def test_topic_and_subtopic_can_move_the_window(self):
        generated = _generated(
            question="Which statement is correct?",
            options=["A. One", "B. Two", "C. Three", "D. Four", "E. Five"],
            topic="Seigniorage",
            sub_topic="Currency issue profit",
        )
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_SEIGNIORAGE],
            generated,
            original_index=0,
        )
        assert out["chunk_changed"] is True
        assert out["selected_validation_chunk_index"] == 1
        assert "seigniorage" in out["excerpt"].lower()

    def test_options_can_move_the_window(self):
        generated = _generated(
            question="Which statement is correct?",
            options=[
                "A. Seigniorage is profit from issuing currency",
                "B. Two",
                "C. Three",
                "D. Four",
                "E. Five",
            ],
            topic="Money",
            sub_topic="Basics",
        )
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_SEIGNIORAGE],
            generated,
            original_index=0,
        )
        assert out["chunk_changed"] is True
        assert out["selected_validation_chunk_index"] == 1

    def test_short_term_qe_reselects_matching_chunk(self):
        generated = _generated(
            question="What does QE do in a crisis?",
            options=["A. Expand", "B. Shrink", "C. Tax", "D. Barter", "E. Salt"],
            topic="Monetary policy",
            sub_topic="QE",
        )
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_QE],
            generated,
            original_index=0,
        )
        assert out["chunk_changed"] is True
        assert out["selected_validation_chunk_index"] == 1
        assert "quantitative easing" in out["excerpt"].lower() or "qe" in out["excerpt"].lower()

    def test_tie_keeps_original_chunk(self):
        twin = CHUNK_SEIGNIORAGE + " extra unused tokens unused tokens."
        out = select_validation_chunk_for_generated(
            [CHUNK_SEIGNIORAGE, twin],
            _generated(),
            original_index=0,
        )
        assert out["chunk_changed"] is False
        assert out["selected_validation_chunk_index"] == 0
        assert out["reason"] == "kept_original_tied_or_better"

    def test_no_probe_hits_keeps_original(self):
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_QE],
            {
                "question": "What is 2 plus 2?",
                "options": ["A. 1", "B. 2", "C. 3", "D. 4", "E. 5"],
                "topic": "Arithmetic",
                "sub_topic": "Addition",
            },
            original_index=0,
        )
        assert out["chunk_changed"] is False
        assert out["selected_validation_chunk_index"] == 0
        assert out["reason"] == "kept_original_no_probe_hits"
        assert out["excerpt"] == CHUNK_BARTER

    def test_single_chunk_stays_original(self):
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER],
            _generated(),
            original_index=0,
        )
        assert out["chunk_changed"] is False
        assert out["selected_validation_chunk_index"] == 0
        assert out["reason"] == "kept_original_only_chunk"

    def test_empty_chunks(self):
        out = select_validation_chunk_for_generated(
            [],
            _generated(),
            original_index=0,
        )
        assert out["excerpt"] == ""
        assert out["chunk_changed"] is False
        assert out["reason"] == "no_chapter_chunks"

    def test_does_not_search_other_chapters(self):
        out = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_SEIGNIORAGE],
            _generated(),
            original_index=0,
        )
        assert OTHER_CHAPTER not in out["excerpt"]
        assert "capital account convertibility" not in out["excerpt"].lower()


class TestValidationChunkDiagnostics:
    def test_event_fields_and_counters(self):
        diag = empty_bank_cost_diagnostics()
        assert diag["validation_chunk_reselection"] == (
            empty_validation_chunk_reselection_diagnostics()
        )
        selection = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_SEIGNIORAGE],
            _generated(),
            original_index=0,
        )
        record_validation_chunk_reselection(diag, selection)
        bucket = diag["validation_chunk_reselection"]
        assert bucket["calls"] == 1
        assert bucket["chunk_changed_count"] == 1
        event = bucket["events"][0]
        assert event["original_chunk_index"] == 0
        assert event["selected_validation_chunk_index"] == 1
        assert event["chunk_changed"] is True
        assert event["match_score"] == selection["match_score"]
        assert event["original_score"] == selection["original_score"]
        assert event["reason"] == "reselected_higher_hits"

    def test_event_cap(self):
        diag = empty_bank_cost_diagnostics()
        for i in range(VALIDATION_CHUNK_RESELECTION_EVENT_LIMIT + 5):
            record_validation_chunk_reselection(
                diag,
                {
                    "original_chunk_index": 0,
                    "selected_validation_chunk_index": i,
                    "chunk_changed": False,
                    "match_score": 0,
                    "original_score": 0,
                    "reason": "kept_original_only_chunk",
                },
            )
        bucket = diag["validation_chunk_reselection"]
        assert bucket["calls"] == VALIDATION_CHUNK_RESELECTION_EVENT_LIMIT + 5
        assert len(bucket["events"]) == VALIDATION_CHUNK_RESELECTION_EVENT_LIMIT

    def test_none_diagnostics_is_safe(self):
        record_validation_chunk_reselection(None, {"chunk_changed": True})


class TestBankBatchHelperAndWiring:
    def test_bank_batch_uses_reselected_excerpt(self):
        slot = _slot()
        chunks = [CHUNK_BARTER, CHUNK_SEIGNIORAGE]
        state = {
            "bank_batch_mode": True,
            "chapter_chunks": {"1": chunks, "2": [OTHER_CHAPTER]},
        }
        diag = empty_bank_cost_diagnostics()
        excerpt = qp._bank_batch_validation_excerpt(
            state, slot, _generated(), chunks, 0, CHUNK_BARTER, diag
        )
        assert "seigniorage" in excerpt.lower()
        assert excerpt == CHUNK_SEIGNIORAGE
        bucket = diag["validation_chunk_reselection"]
        assert bucket["calls"] == 1
        assert bucket["chunk_changed_count"] == 1
        assert bucket["events"][0]["original_chunk_index"] == 0
        assert bucket["events"][0]["selected_validation_chunk_index"] == 1

    def test_final_paper_keeps_generation_excerpt(self):
        slot = _slot()
        chunks = [CHUNK_BARTER, CHUNK_SEIGNIORAGE]
        state = {
            "bank_batch_mode": False,
            "chapter_chunks": {"1": chunks},
        }
        diag = empty_bank_cost_diagnostics()
        excerpt = qp._bank_batch_validation_excerpt(
            state, slot, _generated(), chunks, 0, CHUNK_BARTER, diag
        )
        assert excerpt == CHUNK_BARTER
        assert diag["validation_chunk_reselection"]["calls"] == 0

    def test_helper_stays_inside_selected_chapter_chunks(self):
        slot = _slot(chapter=1)
        chunks = [CHUNK_BARTER, CHUNK_SEIGNIORAGE]
        state = {
            "bank_batch_mode": True,
            "chapter_chunks": {"1": chunks, "2": [OTHER_CHAPTER]},
        }
        excerpt = qp._bank_batch_validation_excerpt(
            state, slot, _generated(), chunks, 0, CHUNK_BARTER, None
        )
        assert "capital account convertibility" not in excerpt.lower()

    def test_fill_and_refill_wire_reselection_before_validators(self):
        fill_src = inspect.getsource(qp.fill_slots)
        refill_src = inspect.getsource(qp.refill_slots)
        assert "_bank_batch_validation_excerpt" in fill_src
        assert "_bank_batch_validation_excerpt" in refill_src
        assert "validation_excerpt" in fill_src
        assert "source_chunk_index\"] = prev_chunk_index" in fill_src
        assert "source_chunk_index\"] = prev_chunk_index" in refill_src
        # Final Paper still validates the generation excerpt.
        assert "slot, generated, state, excerpt, existing_texts" in fill_src
        assert "slot, generated, state, excerpt, existing_texts" in refill_src

    def test_reselected_chunk_feeds_blind_and_cognitive_windows(self):
        selected = select_validation_chunk_for_generated(
            [CHUNK_BARTER, CHUNK_QE],
            {
                "question": "What does QE do in a crisis?",
                "options": ["A. Expand", "B. Shrink", "C. Tax", "D. Barter", "E. Salt"],
                "topic": "Monetary policy",
                "sub_topic": "QE",
            },
            original_index=0,
        )
        snippet = select_blind_solver_source_snippet(
            selected["excerpt"],
            "What does QE do in a crisis?",
            ["A. Expand", "B. Shrink", "C. Tax", "D. Barter", "E. Salt"],
            term_source_text=CHUNK_BARTER + "\n" + CHUNK_QE,
        )
        window = select_cognitive_source_window(
            selected["excerpt"],
            "What does QE do in a crisis? Monetary policy QE",
            term_source_text=CHUNK_BARTER + "\n" + CHUNK_QE,
        )
        assert snippet
        assert "qe" in snippet.lower() or "quantitative easing" in snippet.lower()
        assert window
        assert "qe" in window.lower() or "quantitative easing" in window.lower()
        original_snippet = select_blind_solver_source_snippet(
            CHUNK_BARTER,
            "What does QE do in a crisis?",
            ["A. Expand", "B. Shrink", "C. Tax", "D. Barter", "E. Salt"],
            term_source_text=CHUNK_BARTER + "\n" + CHUNK_QE,
        )
        assert original_snippet == ""


class TestUnchangedRules:
    def test_validator_windows_and_thresholds_unchanged(self):
        assert BANK_BATCH_BLIND_SNIPPET_MAX == 700
        assert BANK_BATCH_VALIDATOR_GROUNDING_MIN == 800
        assert BANK_BATCH_VALIDATOR_GROUNDING_MAX == 1500
        src = inspect.getsource(qp.apply_independent_validation)
        assert "difficulty_score" in src
        assert "validator_unavailable" in src
