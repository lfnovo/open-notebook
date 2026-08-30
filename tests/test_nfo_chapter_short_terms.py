"""Chapter-derived short-term retrieval (Bank Batch evidence windows only).

Offline. Does not change validators, thresholds, acceptance, or Final Paper.
"""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    extract_chapter_short_terms,
    empty_bank_cost_diagnostics,
    evaluate_blind_solver,
    select_blind_solver_source_snippet,
    select_cognitive_source_window,
    select_source_grounding_window,
)


CHAPTER_WITH_ABBREVS = (
    "Central banks may use Quantitative Easing (QE) in a crisis. "
    "M1 is currency and demand deposits. M2 and M3 are broader money aggregates. "
    "A Central Bank Digital Currency (CBDC) is issued by the central bank. "
    "Core Banking Solutions (CBS) connect branches."
)

PADDING = ("barter goods shells salt " * 80)


class TestExtractChapterShortTerms:
    def test_extracts_from_chapter_text_not_a_whitelist(self):
        src = inspect.getsource(extract_chapter_short_terms)
        assert "QE" not in src
        assert "CBDC" not in src
        assert '"m1"' not in src and "'m1'" not in src
        terms = extract_chapter_short_terms(CHAPTER_WITH_ABBREVS)
        assert "qe" in terms
        assert "m1" in terms
        assert "m2" in terms
        assert "m3" in terms
        assert "cbdc" in terms
        assert "cbs" in terms

    def test_absent_from_chapter_is_not_extracted(self):
        terms = extract_chapter_short_terms(
            "People exchanged goods through barter before money existed."
        )
        assert "qe" not in terms
        assert "cbdc" not in terms
        assert "m1" not in terms

    def test_probe_only_text_does_not_invent_chapter_terms(self):
        chapter = "People exchanged goods through barter before money existed."
        extracted = extract_chapter_short_terms(chapter)
        snippet = select_blind_solver_source_snippet(
            chapter,
            "What does QE do to M1 and CBDC holdings?",
            ["A", "B", "C", "D", "E"],
            term_source_text=chapter,
        )
        assert "qe" not in extracted
        assert snippet == ""


class TestBlindShortTermRetrieval:
    def test_short_term_finds_qe_paragraph_when_long_words_miss(self):
        chunk = PADDING + CHAPTER_WITH_ABBREVS + (" tail padding " * 80)
        assert len(chunk) > 700
        diag = empty_bank_cost_diagnostics()
        snippet = select_blind_solver_source_snippet(
            chunk,
            "What does QE do?",
            ["A", "B", "C", "D", "E"],
            term_source_text=CHAPTER_WITH_ABBREVS,
            diagnostics=diag,
        )
        assert snippet
        assert "quantitative easing" in snippet.lower() or "qe" in snippet.lower()
        bucket = diag["short_term_retrieval"]
        assert "qe" in bucket["extracted_short_terms"]
        assert "qe" in bucket["probe_short_terms"]
        assert "qe" in bucket["retrieval_matches"]
        assert bucket["short_term_retrieval_helped_count"] >= 1
        assert bucket["events"][0]["short_term_retrieval_helped"] is True

    def test_m1_m3_and_cbdc_retrieve_from_chapter(self):
        chunk = PADDING + CHAPTER_WITH_ABBREVS + (" zeta " * 80)
        for stem, token in (
            ("Which assets are in M1?", "m1"),
            ("How is M3 broader than M1?", "m3"),
            ("Who issues a CBDC?", "cbdc"),
        ):
            snippet = select_blind_solver_source_snippet(
                chunk,
                stem,
                ["A", "B", "C", "D", "E"],
                term_source_text=CHAPTER_WITH_ABBREVS,
            )
            assert snippet, stem
            assert token in snippet.lower()

    def test_legacy_long_word_retrieval_unchanged(self):
        chunk = ("padding " * 400) + "legal tender currency notes coins " + ("tail " * 400)
        snippet = select_blind_solver_source_snippet(
            chunk,
            "Which item is legal tender currency?",
            ["notes", "barter", "gold", "credit", "cheque"],
        )
        assert snippet
        assert len(snippet) <= 700
        assert "tender" in snippet.lower() or "currency" in snippet.lower()

    def test_unrelated_chunk_still_omits_snippet(self):
        snippet = select_blind_solver_source_snippet(
            "zzz " * 1000,
            "What is 2 + 2?",
            ["1", "2", "3", "4", "5"],
        )
        assert snippet == ""


class TestCognitiveShortTermWindow:
    def test_qe_window_preferred_over_leading_padding(self):
        chunk = PADDING + CHAPTER_WITH_ABBREVS + (" omega " * 40)
        assert len(chunk) > 1500
        diag = empty_bank_cost_diagnostics()
        window = select_cognitive_source_window(
            chunk,
            "Explain QE",
            term_source_text=CHAPTER_WITH_ABBREVS,
            diagnostics=diag,
        )
        assert 800 <= len(window) <= 1500
        assert "qe" in window.lower() or "quantitative easing" in window.lower()
        assert "qe" in diag["short_term_retrieval"]["retrieval_matches"]


class TestGroundingUnchanged:
    def test_terminology_grounded_false_still_rejects(self):
        errors = evaluate_blind_solver(
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
                "terminology_grounded": False,
            },
            [0],
            "single_correct",
        )
        assert any("untaught terminology" in e.lower() for e in errors)

    def test_final_paper_does_not_use_blind_snippet(self):
        blind_src = inspect.getsource(qp._blind_solve)
        assert "if state.get(\"bank_batch_mode\")" in blind_src
        paper_src = inspect.getsource(qp.build_question_paper_graph)
        assert "select_blind_solver_source_snippet" not in paper_src
        assert "select_cognitive_source_window" not in paper_src

    def test_plain_window_api_unchanged_without_extra_terms(self):
        chunk = ("alpha " * 200) + ("currency barter money functions " * 40) + ("omega " * 200)
        window = select_source_grounding_window(chunk, "currency barter money")
        assert 800 <= len(window) <= 1500
        assert "currency" in window.lower()
